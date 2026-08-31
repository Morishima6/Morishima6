#!/usr/bin/env python3

import argparse
import html
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


DAY_PATTERN = re.compile(
    r'data-date="(?P<date>\d{4}-\d{2}-\d{2})"[^>]*></td>\s*'
    r'<tool-tip[^>]*>(?P<label>No contributions|\d+ contributions?) on ',
    re.DOTALL,
)


def fetch_contributions(user: str, end_date: date) -> list[tuple[date, int]]:
    start_date = end_date - timedelta(days=30)
    query = urllib.parse.urlencode({"from": start_date, "to": end_date})
    url = (
        f"https://github.com/users/{urllib.parse.quote(user, safe='')}/contributions"
        f"?{query}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html",
            "Accept-Language": "en-US",
            "User-Agent": "profile-activity-graph",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8")

    counts = {}
    for match in DAY_PATTERN.finditer(page):
        label = match.group("label")
        counts[match.group("date")] = 0 if label == "No contributions" else int(label.split()[0])

    days = []
    for offset in range(31):
        day = start_date + timedelta(days=offset)
        key = day.isoformat()
        if key not in counts:
            raise RuntimeError(f"Contribution data is missing for {key}")
        days.append((day, counts[key]))
    return days


def render_svg(user: str, days: list[tuple[date, int]]) -> str:
    width, height = 920, 300
    left, right, top, bottom = 58, 28, 76, 48
    chart_width = width - left - right
    chart_height = height - top - bottom
    baseline = top + chart_height
    max_count = max(max(count for _, count in days), 1)

    coordinates = []
    for index, (_, count) in enumerate(days):
        x = left + chart_width * index / (len(days) - 1)
        y = baseline - chart_height * count / max_count
        coordinates.append((x, y))

    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in coordinates)
    area_points = f"{left},{baseline} {points} {coordinates[-1][0]:.1f},{baseline}"
    total = sum(count for _, count in days)
    total_label = "contribution" if total == 1 else "contributions"
    safe_user = html.escape(user)

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{safe_user} GitHub contribution activity</title>',
        '<desc id="desc">GitHub contribution counts for the last 31 days.</desc>',
        f'<rect width="{width}" height="{height}" rx="8" fill="#282c34"/>',
        f'<text x="{left}" y="34" fill="#FDFD96" font-family="Segoe UI, Ubuntu, sans-serif" '
        f'font-size="20" font-weight="600">{safe_user} GitHub Contribution Activity</text>',
        f'<text x="{width - right}" y="34" fill="#ABB2BF" font-family="Segoe UI, Ubuntu, sans-serif" '
        f'font-size="13" text-anchor="end">Last 31 days - {total} {total_label}</text>',
    ]

    tick_values = sorted({round(max_count * index / 4) for index in range(5)})
    for value in tick_values:
        y = baseline - chart_height * value / max_count
        elements.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                'stroke="#454B55" stroke-width="1"/>',
                f'<text x="{left - 10}" y="{y + 4:.1f}" fill="#ABB2BF" '
                'font-family="Segoe UI, Ubuntu, sans-serif" font-size="11" '
                f'text-anchor="end">{value}</text>',
            ]
        )

    label_indexes = sorted(set(range(0, len(days), 5)) | {len(days) - 1})
    for index in label_indexes:
        x = coordinates[index][0]
        label = days[index][0].strftime("%b %d")
        elements.append(
            f'<text x="{x:.1f}" y="{height - 20}" fill="#ABB2BF" '
            'font-family="Segoe UI, Ubuntu, sans-serif" font-size="11" '
            f'text-anchor="middle">{label}</text>'
        )

    elements.extend(
        [
            f'<polygon points="{area_points}" fill="#79FE96" fill-opacity="0.20"/>',
            f'<polyline points="{points}" fill="none" stroke="#FDFD96" '
            'stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>',
        ]
    )

    for (day, count), (x, y) in zip(days, coordinates):
        count_label = "contribution" if count == 1 else "contributions"
        elements.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#FFFFFF" '
            f'stroke="#FDFD96" stroke-width="1.5"><title>{day.isoformat()}: '
            f'{count} {count_label}</title></circle>'
        )

    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timezone", default="Asia/Shanghai")
    args = parser.parse_args()

    end_date = datetime.now(ZoneInfo(args.timezone)).date()
    days = fetch_contributions(args.user, end_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(args.user, days), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
