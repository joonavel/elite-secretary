#!/usr/bin/env python3
"""
Generate deterministic hackathon datasets for LLM credit and financial reporting.

Outputs:
- employee_llm_credit_usage.sql
- employee_llm_credit_usage.csv
- employee_llm_financial_usage_2025_h1.sql
- employee_llm_financial_usage_2025_h1.csv
- employee_llm_team_monthly_cost_2025_h1.csv
- employee_llm_team_monthly_tokens_2025_h1.csv
- employee_llm_team_h1_summary_2025_h1.csv
- employee_llm_report_support_2025_h1.json

Optionally:
- insert both tables directly into PostgreSQL when --dsn is provided
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None


SEED = 20260327
REPORT_YEAR = 2025
REPORT_MONTHS = [f"{REPORT_YEAR}-{month:02d}" for month in range(1, 7)]
TEAMS = ["Platform", "Product", "Data", "Security", "Operations"]
PROVIDER_COLUMNS: List[Tuple[str, str, str]] = [
    ("openai_main_credit", "OpenAI", "main"),
    ("openai_small_credit", "OpenAI", "small"),
    ("google_main_credit", "Google", "main"),
    ("google_small_credit", "Google", "small"),
    ("claude_main_credit", "Claude", "main"),
    ("claude_small_credit", "Claude", "small"),
    ("xai_main_credit", "xAI", "main"),
    ("xai_small_credit", "xAI", "small"),
]
PROVIDER_COST_MULTIPLIER: Dict[Tuple[str, str], Decimal] = {
    ("OpenAI", "main"): Decimal("1.18"),
    ("OpenAI", "small"): Decimal("0.84"),
    ("Google", "main"): Decimal("1.02"),
    ("Google", "small"): Decimal("0.72"),
    ("Claude", "main"): Decimal("1.25"),
    ("Claude", "small"): Decimal("0.91"),
    ("xAI", "main"): Decimal("0.97"),
    ("xAI", "small"): Decimal("0.69"),
}
TOKEN_PRICE_PER_1K: Dict[Tuple[str, str], Decimal] = {
    ("OpenAI", "main"): Decimal("0.010"),
    ("OpenAI", "small"): Decimal("0.003"),
    ("Google", "main"): Decimal("0.008"),
    ("Google", "small"): Decimal("0.0024"),
    ("Claude", "main"): Decimal("0.012"),
    ("Claude", "small"): Decimal("0.0036"),
    ("xAI", "main"): Decimal("0.009"),
    ("xAI", "small"): Decimal("0.0028"),
}
TEAM_COST_MULTIPLIER: Dict[str, Decimal] = {
    "Platform": Decimal("1.16"),
    "Product": Decimal("1.08"),
    "Data": Decimal("1.21"),
    "Security": Decimal("0.94"),
    "Operations": Decimal("0.87"),
}
MONTH_BASE_WEIGHTS: List[Decimal] = [
    Decimal("0.143"),
    Decimal("0.149"),
    Decimal("0.158"),
    Decimal("0.167"),
    Decimal("0.181"),
    Decimal("0.202"),
]


@dataclass(frozen=True)
class Employee:
    employee_id: int
    employee_name: str
    employee_type: str


FIRST_NAMES = [
    "김민준", "이서준", "박도윤", "최예준", "정하준", "강지호", "조준우", "윤서진", "장시우", "임현우",
    "한지민", "오하린", "서유진", "신다은", "권채원", "황서아", "안수빈", "송나윤", "전유나", "홍아린",
    "고민재", "문지후", "양태윤", "손은우", "배지안", "백도현", "허주원", "남예린", "심가온", "노서우",
    "류하은", "유준혁", "진서율", "주시온", "우지안", "구하람", "성연우", "나도하", "민서윤", "탁지후",
    "변서현", "채하율", "천시원", "염유찬", "노유빈", "문태오", "배서율", "곽지훈", "원지민", "신예나",
    "유하준", "차서윤", "하도윤", "추민서", "도예린", "황민규", "강하늘", "오지수", "서다온", "권도윤",
    "이주원", "박서연", "최지환", "정유진", "강민석", "조하은", "윤지후", "장예나", "임서준", "한도윤",
    "오서연", "서지안", "신하준", "권예린", "황도윤", "안지후", "송서윤", "전도현", "홍지민", "고예준",
    "문서연", "양하율", "손민준", "배유진", "백지후", "허서연", "남도윤", "심예나", "노지안", "류하준",
    "유서윤", "진도현", "주시원", "우민서", "구지후", "성서연", "나하준", "민도윤", "탁예린", "변지안",
]

LAST_NAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "고", "문", "양", "손", "배", "백", "허", "남", "심", "노",
    "류", "유", "진", "주", "우", "구", "성", "나", "민", "탁",
    "변", "채", "천", "염", "도", "곽", "원", "추", "하", "차",
]

SEED_COLUMNS = [
    "employee_id",
    "employee_name",
    "employee_type",
    "openai_main_credit",
    "openai_small_credit",
    "google_main_credit",
    "google_small_credit",
    "claude_main_credit",
    "claude_small_credit",
    "xai_main_credit",
    "xai_small_credit",
    "total_credit",
]

FINANCIAL_COLUMNS = [
    "year_month",
    "team_name",
    "employee_id",
    "employee_name",
    "employee_type",
    "provider",
    "model_tier",
    "token_usage",
    "cost_usd",
]


def quantize_money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize_int(value: Decimal | float | int | str) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def unique_names(n: int) -> List[str]:
    names: List[str] = []
    used = set()
    idx = 0
    while len(names) < n:
        if idx < len(FIRST_NAMES):
            name = FIRST_NAMES[idx]
        else:
            last = LAST_NAMES[idx % len(LAST_NAMES)]
            name = f"{last}{FIRST_NAMES[idx % len(FIRST_NAMES)][1:]}"
        if name not in used:
            used.add(name)
            names.append(name)
        idx += 1
    return names


def bounded_gauss(rng: random.Random, mean: float, stddev: float, low: float, high: float) -> float:
    for _ in range(1000):
        value = rng.gauss(mean, stddev)
        if low <= value <= high:
            return value
    return min(max(mean, low), high)


def split_decimal_total(total: Decimal, weights: Sequence[Decimal], places: str = "0.01") -> List[Decimal]:
    raw = [(total * weight).quantize(Decimal(places), rounding=ROUND_HALF_UP) for weight in weights]
    diff = total - sum(raw)
    raw[-1] += diff
    return raw


def make_role_weights(rng: random.Random, role: str) -> List[float]:
    if role == "developer":
        base = [0.19, 0.07, 0.15, 0.06, 0.24, 0.12, 0.11, 0.06]
        jitter = [rng.uniform(-0.03, 0.03) for _ in base]
    else:
        base = [0.10, 0.14, 0.08, 0.20, 0.13, 0.21, 0.05, 0.09]
        jitter = [rng.uniform(-0.035, 0.035) for _ in base]
    adjusted = [max(0.01, value + delta) for value, delta in zip(base, jitter)]
    total = sum(adjusted)
    return [value / total for value in adjusted]


def generate_total_credit(rng: random.Random, role: str) -> Decimal:
    if role == "developer":
        bucket = rng.random()
        if bucket < 0.72:
            total = bounded_gauss(rng, 238, 24, 205, 320)
        elif bucket < 0.92:
            total = bounded_gauss(rng, 188, 18, 150, 230)
        else:
            total = bounded_gauss(rng, 300, 16, 260, 340)
    else:
        bucket = rng.random()
        if bucket < 0.74:
            total = bounded_gauss(rng, 74, 18, 18, 98)
        elif bucket < 0.94:
            total = bounded_gauss(rng, 108, 14, 92, 138)
        else:
            total = bounded_gauss(rng, 42, 10, 8, 65)
    return quantize_money(total)


def build_seed_dataset() -> List[Dict[str, object]]:
    rng = random.Random(SEED)
    names = unique_names(100)
    employees: List[Employee] = []
    for idx in range(50):
        employees.append(Employee(idx + 1, names[idx], "developer"))
    for idx in range(50, 100):
        employees.append(Employee(idx + 1, names[idx], "non_developer"))

    rows: List[Dict[str, object]] = []
    for employee in employees:
        total = generate_total_credit(rng, employee.employee_type)
        weights = make_role_weights(rng, employee.employee_type)
        credits = split_decimal_total(total, [Decimal(str(weight)) for weight in weights])
        row = {
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "employee_type": employee.employee_type,
            "openai_main_credit": credits[0],
            "openai_small_credit": credits[1],
            "google_main_credit": credits[2],
            "google_small_credit": credits[3],
            "claude_main_credit": credits[4],
            "claude_small_credit": credits[5],
            "xai_main_credit": credits[6],
            "xai_small_credit": credits[7],
            "total_credit": total,
        }
        assert sum(row[column] for column, _, _ in PROVIDER_COLUMNS) == total
        rows.append(row)
    return rows


def sql_literal(value: object) -> str:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    raise TypeError(f"Unsupported type: {type(value)!r}")


def build_insert_sql(table_name: str, columns: Sequence[str], rows: Iterable[Dict[str, object]]) -> str:
    lines = [f"INSERT INTO {table_name} (", "    " + ",\n    ".join(columns), ")", "VALUES"]
    value_lines = []
    for row in rows:
        values = ", ".join(sql_literal(row[column]) for column in columns)
        value_lines.append(f"    ({values})")
    lines.append(",\n".join(value_lines) + ";")
    return "\n".join(lines) + "\n"


SEED_CREATE_SQL = """\
DROP TABLE IF EXISTS employee_llm_credit_usage;

CREATE TABLE employee_llm_credit_usage (
    employee_id INTEGER PRIMARY KEY,
    employee_name TEXT NOT NULL,
    employee_type TEXT NOT NULL CHECK (employee_type IN ('developer', 'non_developer')),
    openai_main_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    openai_small_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    google_main_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    google_small_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    claude_main_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    claude_small_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    xai_main_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    xai_small_credit NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_credit NUMERIC(10,2) NOT NULL
);
"""

FINANCIAL_CREATE_SQL = """\
DROP TABLE IF EXISTS employee_llm_financial_usage_2025_h1;

CREATE TABLE employee_llm_financial_usage_2025_h1 (
    year_month TEXT NOT NULL,
    team_name TEXT NOT NULL,
    employee_id INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    employee_type TEXT NOT NULL CHECK (employee_type IN ('developer', 'non_developer')),
    provider TEXT NOT NULL,
    model_tier TEXT NOT NULL CHECK (model_tier IN ('main', 'small')),
    token_usage INTEGER NOT NULL,
    cost_usd NUMERIC(12,2) NOT NULL,
    PRIMARY KEY (year_month, employee_id, provider, model_tier)
);
"""


def write_sql_file(create_sql: str, table_name: str, columns: Sequence[str], rows: List[Dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(create_sql)
        handle.write("\n")
        handle.write(build_insert_sql(table_name, columns, rows))


def write_csv_file(rows: Iterable[Dict[str, object]], columns: Sequence[str], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            output: Dict[str, object] = {}
            for key in columns:
                value = row[key]
                if isinstance(value, Decimal):
                    output[key] = f"{value:.2f}"
                else:
                    output[key] = value
            writer.writerow(output)


def normalize_weights(weights: Sequence[Decimal]) -> List[Decimal]:
    total = sum(weights)
    normalized = [(weight / total).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP) for weight in weights]
    normalized[-1] += Decimal("1.0") - sum(normalized)
    return normalized


def month_weights_for_employee(employee_id: int) -> List[Decimal]:
    rng = random.Random(SEED + employee_id * 17)
    jittered = [
        max(Decimal("0.05"), base + Decimal(str(rng.uniform(-0.012, 0.012))))
        for base in MONTH_BASE_WEIGHTS
    ]
    return normalize_weights(jittered)


def employee_team(employee_id: int) -> str:
    return TEAMS[(employee_id - 1) % len(TEAMS)]


def build_financial_dataset(seed_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for seed_row in seed_rows:
        employee_id = int(seed_row["employee_id"])
        employee_type = str(seed_row["employee_type"])
        team_name = employee_team(employee_id)
        month_weights = month_weights_for_employee(employee_id)
        role_multiplier = Decimal("1.12") if employee_type == "developer" else Decimal("0.82")
        team_multiplier = TEAM_COST_MULTIPLIER[team_name]

        for column_name, provider, model_tier in PROVIDER_COLUMNS:
            base_credit = Decimal(str(seed_row[column_name]))
            base_h1_cost = quantize_money(
                base_credit * PROVIDER_COST_MULTIPLIER[(provider, model_tier)] * role_multiplier * team_multiplier
            )
            monthly_costs = split_decimal_total(base_h1_cost, month_weights)

            for month, monthly_cost in zip(REPORT_MONTHS, monthly_costs):
                price_per_1k = TOKEN_PRICE_PER_1K[(provider, model_tier)]
                token_usage = quantize_int((monthly_cost / price_per_1k) * Decimal("1000"))
                rows.append(
                    {
                        "year_month": month,
                        "team_name": team_name,
                        "employee_id": employee_id,
                        "employee_name": str(seed_row["employee_name"]),
                        "employee_type": employee_type,
                        "provider": provider,
                        "model_tier": model_tier,
                        "token_usage": token_usage,
                        "cost_usd": monthly_cost,
                    }
                )
    return rows


def validate_financial_rows(rows: List[Dict[str, object]]) -> None:
    seen = set()
    for row in rows:
        key = (row["year_month"], row["employee_id"], row["provider"], row["model_tier"])
        if key in seen:
            raise ValueError(f"Duplicate financial row found: {key}")
        seen.add(key)

        if row["year_month"] not in REPORT_MONTHS:
            raise ValueError(f"Out-of-range year_month found: {row['year_month']}")
        if row["team_name"] not in TEAMS:
            raise ValueError(f"Unknown team_name found: {row['team_name']}")
        if row["provider"] not in {provider for _, provider, _ in PROVIDER_COLUMNS}:
            raise ValueError(f"Unknown provider found: {row['provider']}")
        if row["model_tier"] not in {"main", "small"}:
            raise ValueError(f"Unknown model_tier found: {row['model_tier']}")
        if not isinstance(row["token_usage"], int) or row["token_usage"] < 0:
            raise ValueError(f"Invalid token_usage found: {row['token_usage']}")
        cost = row["cost_usd"]
        if not isinstance(cost, Decimal) or cost < Decimal("0.00"):
            raise ValueError(f"Invalid cost_usd found: {cost}")


def aggregate_sum(rows: Iterable[Dict[str, object]], key_names: Sequence[str], value_name: str) -> Dict[Tuple[object, ...], Decimal | int]:
    aggregated: Dict[Tuple[object, ...], Decimal | int] = {}
    for row in rows:
        key = tuple(row[name] for name in key_names)
        current = aggregated.get(key)
        value = row[value_name]
        if current is None:
            aggregated[key] = value
        else:
            aggregated[key] = current + value
    return aggregated


def build_team_monthly_cost(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    aggregated = aggregate_sum(rows, ["team_name", "year_month"], "cost_usd")
    table_rows: List[Dict[str, object]] = []
    for team in TEAMS:
        month_values = [quantize_money(aggregated[(team, month)]) for month in REPORT_MONTHS]
        h1_total = quantize_money(sum(month_values, Decimal("0.00")))
        monthly_avg = quantize_money(h1_total / Decimal(len(REPORT_MONTHS)))
        table_rows.append(
            {
                "team_name": team,
                **{month: month_values[idx] for idx, month in enumerate(REPORT_MONTHS)},
                "h1_total_cost_usd": h1_total,
                "monthly_avg_cost_usd": monthly_avg,
            }
        )
    return table_rows


def build_team_monthly_tokens(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    aggregated = aggregate_sum(rows, ["team_name", "year_month"], "token_usage")
    table_rows: List[Dict[str, object]] = []
    for team in TEAMS:
        month_values = [int(aggregated[(team, month)]) for month in REPORT_MONTHS]
        h1_total = sum(month_values)
        monthly_avg = round(h1_total / len(REPORT_MONTHS))
        table_rows.append(
            {
                "team_name": team,
                **{month: month_values[idx] for idx, month in enumerate(REPORT_MONTHS)},
                "h1_total_tokens": h1_total,
                "monthly_avg_tokens": monthly_avg,
            }
        )
    return table_rows


def build_team_h1_summary(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    cost_by_team = aggregate_sum(rows, ["team_name"], "cost_usd")
    tokens_by_team = aggregate_sum(rows, ["team_name"], "token_usage")
    total_cost = quantize_money(sum(cost_by_team.values(), Decimal("0.00")))
    summary_rows: List[Dict[str, object]] = []
    for team in TEAMS:
        team_cost = quantize_money(cost_by_team[(team,)])
        team_tokens = int(tokens_by_team[(team,)])
        share = (team_cost / total_cost).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if total_cost else Decimal("0.0000")
        summary_rows.append(
            {
                "team_name": team,
                "h1_total_cost_usd": team_cost,
                "h1_total_tokens": team_tokens,
                "cost_share_pct": share,
                "monthly_avg_cost_usd": quantize_money(team_cost / Decimal(len(REPORT_MONTHS))),
            }
        )
    return summary_rows


def build_support_payload(
    cost_rows: List[Dict[str, object]],
    token_rows: List[Dict[str, object]],
    summary_rows: List[Dict[str, object]],
) -> Dict[str, object]:
    total_cost = quantize_money(sum(Decimal(str(row["h1_total_cost_usd"])) for row in summary_rows))
    total_tokens = sum(int(row["h1_total_tokens"]) for row in summary_rows)
    top_team = max(summary_rows, key=lambda row: Decimal(str(row["h1_total_cost_usd"])))
    highest_share_team = max(summary_rows, key=lambda row: Decimal(str(row["cost_share_pct"])))

    totals_by_month = {
        month: quantize_money(sum(Decimal(str(row[month])) for row in cost_rows))
        for month in REPORT_MONTHS
    }
    growth_pairs = []
    for previous, current in zip(REPORT_MONTHS, REPORT_MONTHS[1:]):
        delta = quantize_money(totals_by_month[current] - totals_by_month[previous])
        growth_pairs.append((previous, current, delta))
    steepest_growth = max(growth_pairs, key=lambda item: item[2])

    main_cost = Decimal("0.00")
    small_cost = Decimal("0.00")
    for row in build_financial_dataset(build_seed_dataset()):
        if row["model_tier"] == "main":
            main_cost += row["cost_usd"]
        else:
            small_cost += row["cost_usd"]
    main_share = (main_cost / (main_cost + small_cost)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    insights = [
        f"H1 총비용은 ${total_cost:.2f}이며, 가장 비용이 큰 팀은 {top_team['team_name']} 팀으로 ${Decimal(str(top_team['h1_total_cost_usd'])):.2f}를 사용했다.",
        f"비용 점유율이 가장 높은 팀은 {highest_share_team['team_name']} 팀이며 전체 비용의 {Decimal(str(highest_share_team['cost_share_pct'])) * Decimal('100'):.2f}%를 차지한다.",
        f"전사 비용은 {steepest_growth[0]}에서 {steepest_growth[1]}로 넘어가며 가장 크게 증가했고 증가액은 ${steepest_growth[2]:.2f}다.",
    ]
    patterns = [
        f"main tier 비용 비중은 전체의 {main_share * Decimal('100'):.2f}%로, 고성능 모델 사용이 비용 구조를 주도한다.",
        f"총 토큰 사용량은 {total_tokens:,}이며 팀별 비용 차이에 비해 토큰 총량 차이는 완만해 단가가 높은 모델 사용 편중이 존재한다.",
    ]
    recommendations = [
        f"{top_team['team_name']} 팀은 반복성 업무를 small tier 모델로 전환할 후보가 가장 크다.",
        f"{steepest_growth[1]} 사용량 급증 원인을 점검해 배치 작업 또는 집중 사용 이벤트 여부를 확인하는 것이 좋다.",
        "고비용 팀에는 provider별 예산 한도와 월간 모니터링 기준선을 함께 두는 것이 적절하다.",
    ]

    return {
        "report_period": "2025 H1",
        "data_source": "generated from employee_llm_credit_usage.csv seed dataset",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "seed": SEED,
        "teams": TEAMS,
        "months": REPORT_MONTHS,
        "insights": insights,
        "patterns": patterns,
        "recommendations": recommendations,
        "totals": {
            "h1_total_cost_usd": f"{total_cost:.2f}",
            "h1_total_tokens": total_tokens,
            "main_tier_share_pct": f"{(main_share * Decimal('100')):.2f}",
        },
    }


def write_json(payload: Dict[str, object], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def insert_postgres(seed_rows: List[Dict[str, object]], financial_rows: List[Dict[str, object]], dsn: str) -> None:
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Install psycopg[binary] or run without --dsn.")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(SEED_CREATE_SQL)
            cur.executemany(
                f"INSERT INTO employee_llm_credit_usage ({', '.join(SEED_COLUMNS)}) VALUES ({', '.join(['%s'] * len(SEED_COLUMNS))})",
                [[row[column] for column in SEED_COLUMNS] for row in seed_rows],
            )
            cur.execute(FINANCIAL_CREATE_SQL)
            cur.executemany(
                f"INSERT INTO employee_llm_financial_usage_2025_h1 ({', '.join(FINANCIAL_COLUMNS)}) VALUES ({', '.join(['%s'] * len(FINANCIAL_COLUMNS))})",
                [[row[column] for column in FINANCIAL_COLUMNS] for row in financial_rows],
            )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic LLM credit and financial datasets.")
    parser.add_argument("--output-dir", default=".", help="Directory for generated outputs")
    parser.add_argument("--dsn", help="Optional PostgreSQL DSN for direct insert")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    seed_rows = build_seed_dataset()
    financial_rows = build_financial_dataset(seed_rows)
    validate_financial_rows(financial_rows)

    team_monthly_cost = build_team_monthly_cost(financial_rows)
    team_monthly_tokens = build_team_monthly_tokens(financial_rows)
    team_h1_summary = build_team_h1_summary(financial_rows)
    support_payload = build_support_payload(team_monthly_cost, team_monthly_tokens, team_h1_summary)

    write_sql_file(
        SEED_CREATE_SQL,
        "employee_llm_credit_usage",
        SEED_COLUMNS,
        seed_rows,
        output_dir / "employee_llm_credit_usage.sql",
    )
    write_csv_file(seed_rows, SEED_COLUMNS, output_dir / "employee_llm_credit_usage.csv")

    write_sql_file(
        FINANCIAL_CREATE_SQL,
        "employee_llm_financial_usage_2025_h1",
        FINANCIAL_COLUMNS,
        financial_rows,
        output_dir / "employee_llm_financial_usage_2025_h1.sql",
    )
    write_csv_file(financial_rows, FINANCIAL_COLUMNS, output_dir / "employee_llm_financial_usage_2025_h1.csv")

    cost_columns = ["team_name", *REPORT_MONTHS, "h1_total_cost_usd", "monthly_avg_cost_usd"]
    token_columns = ["team_name", *REPORT_MONTHS, "h1_total_tokens", "monthly_avg_tokens"]
    summary_columns = ["team_name", "h1_total_cost_usd", "h1_total_tokens", "cost_share_pct", "monthly_avg_cost_usd"]
    write_csv_file(team_monthly_cost, cost_columns, output_dir / "employee_llm_team_monthly_cost_2025_h1.csv")
    write_csv_file(team_monthly_tokens, token_columns, output_dir / "employee_llm_team_monthly_tokens_2025_h1.csv")
    write_csv_file(team_h1_summary, summary_columns, output_dir / "employee_llm_team_h1_summary_2025_h1.csv")
    write_json(support_payload, output_dir / "employee_llm_report_support_2025_h1.json")

    if args.dsn:
        insert_postgres(seed_rows, financial_rows, args.dsn)

    print(f"Generated seed rows: {len(seed_rows)}")
    print(f"Generated financial rows: {len(financial_rows)}")
    print(f"Output directory: {output_dir}")
    print("Files:")
    for file_name in [
        "employee_llm_credit_usage.sql",
        "employee_llm_credit_usage.csv",
        "employee_llm_financial_usage_2025_h1.sql",
        "employee_llm_financial_usage_2025_h1.csv",
        "employee_llm_team_monthly_cost_2025_h1.csv",
        "employee_llm_team_monthly_tokens_2025_h1.csv",
        "employee_llm_team_h1_summary_2025_h1.csv",
        "employee_llm_report_support_2025_h1.json",
    ]:
        print(f" - {output_dir / file_name}")
    if args.dsn:
        print("PostgreSQL insert completed.")


if __name__ == "__main__":
    main()
