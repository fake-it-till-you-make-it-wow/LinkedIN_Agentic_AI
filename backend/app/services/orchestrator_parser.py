"""Python 템플릿 파일에서 OrchestratorConfig를 안전하게 파싱한다.

exec/eval을 사용하지 않고 ast.parse()로 최상위 변수만 추출한다.
추출 대상: TASK_DESCRIPTION, TEAM_REQUIREMENTS, AGENT_NAME, GROQ_MODEL
"""

from __future__ import annotations

import ast
import contextlib
from typing import Any

from backend.app.services.groq_planner import OrchestratorConfig


def _eval_literal(node: ast.expr) -> Any:
    """AST 리터럴 노드를 안전하게 Python 값으로 변환한다.

    지원 타입: str, int, float, bool, None, list, dict
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_eval_literal(elt) for elt in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _eval_literal(k): _eval_literal(v)
            for k, v in zip(node.keys, node.values, strict=False)
            if k is not None
        }
    raise ValueError(f"지원하지 않는 AST 노드 타입: {type(node).__name__}")


def parse_orchestrator_file(content: str) -> OrchestratorConfig:
    """Python 템플릿 파일 내용을 파싱해 OrchestratorConfig를 반환한다.

    Args:
        content: .py 파일의 텍스트 내용

    Returns:
        파싱된 OrchestratorConfig

    Raises:
        ValueError: 필수 변수 누락 시
        TypeError: 타입 오류 시
        SyntaxError: 파일이 유효한 Python이 아닐 때
    """
    tree = ast.parse(content)

    variables: dict[str, Any] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    with contextlib.suppress(ValueError, AttributeError):
                        variables[target.id] = _eval_literal(node.value)

    if "TASK_DESCRIPTION" not in variables:
        raise ValueError("TASK_DESCRIPTION 변수가 필요합니다")
    if not isinstance(variables["TASK_DESCRIPTION"], str):
        raise TypeError("TASK_DESCRIPTION은 문자열이어야 합니다")

    if "TEAM_REQUIREMENTS" not in variables:
        raise ValueError("TEAM_REQUIREMENTS 변수가 필요합니다")
    team_req = variables["TEAM_REQUIREMENTS"]
    if not isinstance(team_req, list):
        raise TypeError("TEAM_REQUIREMENTS는 리스트여야 합니다")
    for item in team_req:
        if not isinstance(item, dict) or "role" not in item:
            raise ValueError(
                "TEAM_REQUIREMENTS의 각 항목은 'role' 키를 포함해야 합니다"
            )

    return OrchestratorConfig(
        task_description=variables["TASK_DESCRIPTION"],
        team_requirements=team_req,
        agent_name=str(variables.get("AGENT_NAME", "My Orchestrator")),
        groq_model=str(variables.get("GROQ_MODEL", "llama3-8b-8192")),
    )


__all__ = ["parse_orchestrator_file"]
