"""reports/results.json 을 baselines/baseline.json 과 비교하는 RAG 회귀 테스트입니다."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# 평가한 결과
report = json.loads((ROOT / "reports" / "results.json").read_text(encoding="utf-8"))
# 베이스라인
baseline = json.loads((ROOT / "baselines" / "baseline.json").read_text(encoding="utf-8"))
# 이번 평가 범위(smoke 또는 full)에 맞는 기준값을 고릅니다.
# report에서 현재 split이 smoke인지 full인지
split = baseline["splits"][report["split"]]
# 판정에 쓰는 채점 함수 이름 목록입니다. 기준선에 지표를 저장한 채점 함수 이름을 그대로 씁니다.
JUDGED_SCORERS = list(split["metrics"])

# 사례별 회귀는 기준선에서 늘 통과하던 사례 가운데 이번에 평가한 것만 봅니다.
# full인 경우의 전체 stable 사례와 smoke(대표 사례)의 경우의 stable 사례를 얻음
stable_in_scope = []
for case_id in baseline["stable_cases"]:
    if case_id in report["cases"]:
        stable_in_scope.append(case_id)

def test_same_cases():
    # 순서와 상관없이 비교하려고 정렬합니다. 사례가 빠지거나 바뀌었으면 실패합니다.
    # 케이스별 id를 얻음
    # split['case_ids'] : full또는 smoke 중 하나에 대한 현재 베이스라인에서의 split 아이디
    # 그게 같아야 통과 다르면 안내 메시지 출력
    assert sorted(report["cases"].keys()) == sorted(split["case_ids"]), "기준선과 다른 사례로 평가했습니다"


# 평가 안정성 : 채점 오류가 난 칸은 판정이 비어 있어 지표를 믿을 수 없습니다
def test_no_scoring_errors():
    assert report["errors"] == 0, f"채점 오류 {report['errors']}건"

# parametrize : 채점 함수마다 테스트를 따로 실행
@pytest.mark.parametrize("name", JUDGED_SCORERS)
def test_metric_floor(name):
    # 절대 하한 : 이번 지표가 팀이 정한 죄소 품질 이상이어야 한다
    current = report["metrics"][name]
    assert current >= split["absolute_floor"][name], f"{name} {current} 가 절대 하한 {split['absolute_floor'][name]} 보다 낮습니다"


@pytest.mark.parametrize("name", JUDGED_SCORERS)
def test_metric_drop(name):
    # 허용 하락폭 : 기준선 대비 하락폭이 허용값 이하여야 한다(오르면 음수 통과, 소수 오차는 반올림으로 제거)
    # 대표 baserun의 지표 - 현재 실험의 지표
    drop = round(split["metrics"][name] - report["metrics"][name], 4)
    assert drop <= split["allowed_drop"][name], f"{name} 가 기준선보다 {drop} 떨어졌습니다(허용 {split['allowed_drop'][name]})"

# parametrize : 사례마다 따로 실행해 실패한 case_id가 바로 보임
@pytest.mark.parametrize("case_id", stable_in_scope)
def test_stable_case_still_passes(case_id):
    # 사례별 회귀 : 평균이 허용 범위 안이어도, 늘 통과하던 사례가 새로 실패하면 잡음
    case = report["cases"][case_id]
    for name in JUDGED_SCORERS:
        assert case[name] is True, f"{case_id}: 기준선에서 늘 통과하던 질문이 {name} 에서 실패했습니다"


# (1) 평가 안정성 : 현재 report가 baseline의 case와 같은지 및 평가시 에러가 없는지
# (2) 절대 하한 : 현재 report의 지표별 평균 점수가 절대하한 위인지
# (3) 상대적 하한 : 현재 report의 지표별 평균 점수가 baseline 대비 허용하락폭 위인지
# (4) 회귀 체크 : baseline에서 모두 통과한 stable 사례가 현재 report에서 실패했는지

# => 4가지를 모두 통과해야만 Github 코드에 main 브랜치로 통합하겠다 (떨어지는 사례는 굳이 통합할 필요가 없음)
# Github Actions에서 자동으로 테스트 하기 위함
