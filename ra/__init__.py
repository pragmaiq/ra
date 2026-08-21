"""
ra — Iraqi Arabic data cleaning pipeline

Usage:
  SWEPT="data/swept/iraq.jsonl,data/swept/iraq_comments.jsonl" ra

Or with all files:
  SWEPT=$(find data/swept -name "*.jsonl" | tr '\n' ',') ra
"""

import json
import multiprocessing as mp
import time
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from ra.settings import POISON_PILL, SWEPT, WORKERS
from ra.worker import worker_fn
from ra.writer import writer_fn

console = Console()


def _count_lines(path: Path) -> int:
    count = 0
    with open(path, "rb") as f:
        for _ in f:
            count += 1
    return count


def _writer_wrapper(clean_queue: mp.Queue, result_queue: mp.Queue) -> None:
    """Module-level — must NOT be inside main() or macOS spawn can't pickle it."""
    result = writer_fn(clean_queue)
    result_queue.put(result)


def _producer(
    files: list[Path],
    raw_queue: mp.Queue,
    progress_queue: mp.Queue,
    worker_count: int,
) -> None:
    for file_path in files:
        filename = file_path.name
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    raw_queue.put((line, filename))
                    progress_queue.put(("line", filename))
    for _ in range(worker_count):
        raw_queue.put(POISON_PILL)


def _build_stats_table(
    worker_stats: list[dict], written: int, duplicates: int, elapsed: float
) -> Table:
    total_processed = sum(s["processed"] for s in worker_stats)
    total_accepted  = sum(s["accepted"]  for s in worker_stats)
    all_rejected: dict[str, int] = defaultdict(int)
    for s in worker_stats:
        for reason, count in s.get("rejected", {}).items():
            all_rejected[reason] += count

    table = Table(title="Pipeline Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Count", justify="right", style="bold")

    table.add_row("Lines processed",    f"{total_processed:,}")
    table.add_row("Accepted",           f"{total_accepted:,}",  style="green")
    table.add_row("Written to file",    f"{written:,}",         style="bold green")
    table.add_row("Duplicates skipped", f"{duplicates:,}",      style="yellow")
    table.add_row("", "")
    table.add_row("[bold]Rejection reasons[/bold]", "")
    for reason, count in sorted(all_rejected.items(), key=lambda x: -x[1]):
        table.add_row(f"  {reason}", f"{count:,}", style="red")
    table.add_row("", "")
    table.add_row("Time elapsed", f"{elapsed:.1f}s")
    if elapsed > 0:
        table.add_row("Processing rate", f"{total_processed / elapsed:,.0f} lines/sec")

    return table


def main() -> None:
    if not SWEPT:
        console.print("[red]Error: SWEPT env var is empty.[/red]")
        raise SystemExit(1)

    files: list[Path] = []
    for path_str in SWEPT:
        p = Path(path_str)
        if not p.exists():
            console.print(f"[yellow]⚠ File not found, skipping: {p}[/yellow]")
            continue
        files.append(p)

    if not files:
        console.print("[red]No valid files found.[/red]")
        raise SystemExit(1)

    console.print(f"\n[bold cyan]ra[/bold cyan] — Iraqi Arabic data cleaning pipeline")
    console.print(f"[dim]Files   : {len(files)}[/dim]")
    console.print(f"[dim]Workers : {WORKERS}[/dim]")
    console.print(f"[dim]Output  : data/raw.jsonl[/dim]\n")

    console.print("[dim]Counting lines...[/dim]")
    line_counts: dict[str, int] = {}
    for f in files:
        line_counts[f.name] = _count_lines(f)
        console.print(f"  [dim]{f.name}: {line_counts[f.name]:,} lines[/dim]")

    total_lines = sum(line_counts.values())
    console.print(f"\n[dim]Total: {total_lines:,} lines[/dim]\n")

    manager        = mp.Manager()
    raw_queue      = manager.Queue(maxsize=10_000)
    clean_queue    = manager.Queue(maxsize=10_000)
    progress_queue = manager.Queue()
    result_queue   = manager.Queue()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TextColumn("[dim]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    file_tasks: dict[str, TaskID] = {}

    with progress:
        for f in files:
            task_id = progress.add_task(f.name, total=line_counts[f.name])
            file_tasks[f.name] = task_id
        overall_task = progress.add_task("[bold white]TOTAL", total=total_lines)

        start_time = time.time()

        writer_proc = mp.Process(
            target=_writer_wrapper,
            args=(clean_queue, result_queue),
        )
        writer_proc.start()

        worker_procs = []
        for i in range(WORKERS):
            p = mp.Process(target=worker_fn, args=(raw_queue, clean_queue, i))
            p.start()
            worker_procs.append(p)

        producer_proc = mp.Process(
            target=_producer,
            args=(files, raw_queue, progress_queue, WORKERS),
        )
        producer_proc.start()

        lines_done = 0
        while lines_done < total_lines:
            try:
                msg_type, filename = progress_queue.get(timeout=0.1)
                if msg_type == "line":
                    if filename in file_tasks:
                        progress.advance(file_tasks[filename])
                    progress.advance(overall_task)
                    lines_done += 1
            except Exception:
                if not producer_proc.is_alive():
                    break

        producer_proc.join()
        for p in worker_procs:
            p.join()
        writer_proc.join()

    elapsed = time.time() - start_time
    result  = result_queue.get()

    console.print()
    console.print(_build_stats_table(
        result["worker_stats"],
        result["written"],
        result["duplicates"],
        elapsed,
    ))
    console.print(f"\n[bold green]✅ Done — {result['written']:,} entries written to data/raw.jsonl[/bold green]\n")