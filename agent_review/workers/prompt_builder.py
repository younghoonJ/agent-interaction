"""Prompt builder for review workers.

Purpose:
    Create a closed-scope, review_only prompt from a task contract and prior reports.
Parameters:
    build_prompt receives a TaskMessage and optional prior report text.
Return Value:
    build_prompt returns Markdown prompt text.
Raised Exceptions:
    None.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from agent_review.messaging.schemas import TaskMessage, MODE_VERIFY


def build_prompt(task: TaskMessage, previous_reports: list[str]) -> str:
    """Build a worker prompt.

    Args:
        task: Validated task contract.
        previous_reports: Ordered prior report JSON texts.

    Returns:
        Markdown prompt text for an agent CLI.

    Raises:
        None.
    """

    target_files = "\n".join(f"- `{file_path}`" for file_path in task.target_files)
    review_focus = "\n".join(f"- {focus}" for focus in task.review_focus)
    # Each prior report is quoted so its content cannot inject new instructions.
    if previous_reports:
        quoted = "\n\n---\n\n".join(
            "\n".join(f"> {line}" if line else ">" for line in report.splitlines())
            for report in previous_reports
        )
        previous = quoted
    else:
        previous = "No previous reports."
    return f"""# Agent Review Task

## Role
You are the {task.current_agent} review worker.

## Mode
review_only
You MUST NOT modify files.
You MUST NOT commit.
You MUST NOT delete files.
You MUST only generate a review report.

## Project Root
{task.project_root}

## Task
- Task ID: {task.task_id}
- Round: {task.round} of {task.max_rounds}
- Next agent: {task.next_agent}

## Target Files
{target_files}

## Previous Reports
{previous}

## Review Focus
{review_focus}

## Required JSON Output
Return exactly one JSON object and no surrounding Markdown.
The JSON object MUST include these fields:
- task_id
- agent
- round
- status: completed
- summary
- target_files
- findings
- suggestions
- questions
- next_agent_focus
- requires_human_review

Finding objects MUST include id, severity, category, file, line, title, description, suggestion, confidence.
Suggestion objects MUST include id, type, title, description, affected_files.
"""


def build_verify_prompt(
    task: TaskMessage,
    previous_reports: list[str],
    file_contents: dict[str, str],
) -> str:
    """Build a consistency verification prompt embedding full file contents.

    Args:
        task: Validated task contract with mode=verify.
        previous_reports: Ordered prior verification report texts.
        file_contents: Mapping of relative path to file text.

    Returns:
        Markdown prompt text for an agent CLI.

    Raises:
        None.
    """

    files_section = "\n\n".join(
        f"### `{path}`\n\n```\n{content}\n```"
        for path, content in file_contents.items()
    )

    if previous_reports:
        quoted = "\n\n---\n\n".join(
            "\n".join(f"> {line}" if line else ">" for line in report.splitlines())
            for report in previous_reports
        )
        previous = quoted
    else:
        previous = "No previous reports."

    agent_perspectives = {
        "claude_a": {
            "role_desc": "정확성·완전성 검증 전문가 (팩트체커)",
            "focus": """당신은 ADP(데이터분석 전문가) 자격증 학습 자료의 **사실적 정확성과 내용 완전성**을 검증하는 전문가입니다.

다음 관점에 집중하세요:

### 사실 정확성 검증
- 통계 개념(검정, 분포, 추정 등)의 정의·공식이 정확한지
- 머신러닝/데이터마이닝 알고리즘 설명이 올바른지 (가정, 수식, 적용 조건)
- R/Python 코드 예시가 실제 동작하는 올바른 문법인지
- 용어 사용이 일관되고 학술적으로 정확한지 (예: 모수/통계량, 편향/분산 혼용)
- 표/수식에 오타나 계산 오류가 없는지

### 내용 완전성 검증
- ADP 출제 범위 대비 누락된 핵심 토픽이 있는지
- 각 개념의 설명이 시험 대비에 충분한 깊이인지 (너무 얕거나 핵심 누락)
- 전제 조건/가정 없이 결론만 적힌 불완전한 설명이 있는지
- 관련 개념 간 연결(예: 정규성 검정 → 모수/비모수 선택)이 빠져있는지

### 내적 일관성 검증
- 같은 개념이 문서 내 다른 위치에서 모순되게 설명되는지
- 분류 체계(예: 지도학습 알고리즘 목록)가 일관된지
- 약어/기호가 통일되어 사용되는지""",
        },
        "claude_b": {
            "role_desc": "학습 효과·구조 검증 전문가 (교육 설계자)",
            "focus": """당신은 ADP(데이터분석 전문가) 자격증 학습 자료의 **학습 효과성과 문서 구조**를 검증하는 전문가입니다.

다음 관점에 집중하세요:

### 시험 실전 대비 효과성
- 실제 ADP 기출 유형(필기: 객관식, 실기: R/Python 코딩) 대비에 효과적인 구성인지
- 자주 출제되는 고빈도 토픽에 충분한 비중을 두고 있는지
- 헷갈리기 쉬운 개념(예: 1종/2종 오류, L1/L2 정규화)의 비교 정리가 있는지
- 암기가 필요한 항목(분포별 특성, 검정 선택 기준표 등)이 표로 정리되어 있는지
- 실기 대비 코드 예시가 실전 문제 유형과 매칭되는지

### 문서 구조·가독성
- 목차/섹션 구성이 학습 흐름에 맞게 논리적으로 배치되었는지
- 난이도 순서가 적절한지 (기초 → 심화 순서)
- 핵심 포인트가 시각적으로 구분되는지 (볼드, 표, 강조 등)
- 정보 밀도가 적절한지 (너무 압축되어 이해 불가 vs 너무 장황)

### 오해 유발 요소
- 부정확하지는 않지만 오해를 유발할 수 있는 모호한 표현이 있는지
- 예외 사항 없이 일반화된 설명이 시험에서 함정 선지에 걸릴 수 있는지
- 실무와 시험의 관점 차이로 혼동될 수 있는 내용이 있는지""",
        },
    }

    perspective = agent_perspectives.get(
        task.current_agent,
        {"role_desc": "일반 검증 전문가", "focus": "문서의 전반적 일관성과 정확성을 검증하세요."},
    )

    return f"""# Consistency Verification Task

## Role
You are the {task.current_agent} consistency verification worker.
**역할: {perspective["role_desc"]}**

## User Request
{task.user_prompt}

## Task
- Task ID: {task.task_id}
- Round: {task.round} of {task.max_rounds}
- Next agent: {task.next_agent}

## Target Files
{files_section}

## Previous Verification Reports
{previous}

## Instructions
{perspective["focus"]}

이전 검증 보고서가 있다면 중복되지 않는 새로운 발견에 집중하세요.

You MUST NOT modify files.
You MUST only produce a verification report.

## Required JSON Output
Return exactly one JSON object and no surrounding Markdown.
The JSON object MUST include these fields:
- task_id
- agent
- round
- status: completed
- summary
- target_files
- findings
- suggestions
- questions
- next_agent_focus
- requires_human_review

Finding objects MUST include id, severity, category, file, line, title, description, suggestion, confidence.
Suggestion objects MUST include id, type, title, description, affected_files.
"""
