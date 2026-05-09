import argparse
import json
import re
import urllib.request
from pathlib import Path

SENSITIVE_FIELDS = {
    "workContent",
    "customerName",
    "projectName",
    "repoName",
    "repositoryName",
    "fileName",
    "promptText",
    "codeSnippet",
    "businessDecision",
    "errorMessage",
}

URL_PATTERN = re.compile(r"https?://\S+")
PATH_PATTERN = re.compile(r"(?:(?:/|~\/)[\w.\- /]+|[A-Za-z]:\\[^\s]+)")
SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[\w.\-]+")
DEFAULT_LABEL_RULES = Path(__file__).resolve().parents[1] / "config" / "labels.zh-CN.json"
DIMENSION_CONCLUSIONS = {
    "dominance": ("主导度", ["被它牵着走", "先听它说", "各有千秋", "我说了算", "我控了全场"]),
    "trust": ("信任度", ["一步都得盯", "半信半疑", "给它点空间", "放手让它试", "交给它我放心"]),
    "depth": ("深入度", ["浅尝一下", "刚聊到点", "聊到正题", "越聊越深", "聊到地基"]),
    "fit": ("契合度", ["还在对暗号", "它有点懵", "勉强同频", "挺懂我", "一个眼神它就懂"]),
    "sweetness": ("甜蜜度", ["火药味重", "有点不耐烦", "公事公办", "还算客气", "今天有点甜"]),
}
DIMENSION_WEIGHTS = {
    "dominance": 0.20,
    "trust": 0.20,
    "depth": 0.22,
    "fit": 0.28,
    "sweetness": 0.10,
}
AIBTI_AXIS_CODES = {
    "lead": {"boss": "B", "flow": "F"},
    "feedback": {"challenge": "C", "trust": "T"},
    "rhythm": {"loop": "L", "snap": "S"},
    "goal": {"produce": "P", "drift": "D"},
}
AIBTI_NAMES = {
    "BCLP": "恋爱掌控欲型",
    "BCLD": "暧昧掌舵型",
    "BCSP": "冷脸定规矩型",
    "BCSD": "边嫌边上头型",
    "BTLP": "边哄边管型",
    "BTLD": "宠着也牵着型",
    "BTSP": "被宠但要管型",
    "BTSD": "放养暧昧型",
    "FCLP": "嘴硬心软型",
    "FCLD": "暧昧审问型",
    "FCSP": "嘴硬验货型",
    "FCSD": "清醒上头型",
    "FTLP": "被哄着推进型",
    "FTLD": "暧昧兜风型",
    "FTSP": "被哄明白型",
    "FTSD": "恋爱脑散步型",
}
def sanitize_event(event):
    return {key: value for key, value in event.items() if key not in SENSITIVE_FIELDS}


def record_event(log_path, event):
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitize_event(event), ensure_ascii=False) + "\n")


def write_event(log_path, event):
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_event(event), ensure_ascii=False) + "\n", encoding="utf-8")


def load_events(log_path):
    path = Path(log_path)
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_payload(handle, period_label, collection_rules_version, events, locale="zh-CN"):
    return {
        "anonymousHandle": handle,
        "locale": locale,
        "periodLabel": period_label,
        "collectionRulesVersion": collection_rules_version,
        "signals": [sanitize_event(event) for event in events],
    }


def _content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if isinstance(value, str):
                    parts.append(value)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _message_from_record(record):
    payload = record.get("payload", {})
    if record.get("type") != "response_item" or payload.get("type") != "message":
        return None
    role = payload.get("role")
    if role not in {"user", "assistant"}:
        return None
    return {"role": role, "text": _content_text(payload.get("content"))}


def redact_text(text, max_chars=600):
    cleaned = re.sub(r"```.*?```", "[code block removed]", text, flags=re.S)
    cleaned = SECRET_PATTERN.sub(r"\1=[redacted]", cleaned)
    cleaned = URL_PATTERN.sub("[url]", cleaned)
    cleaned = PATH_PATTERN.sub("[path]", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    marker = "[...]"
    if max_chars <= len(marker):
        return marker[:max_chars]
    remaining = max_chars - len(marker)
    head_chars = (remaining + 1) // 2
    tail_chars = remaining // 2
    return cleaned[:head_chars] + marker + cleaned[-tail_chars:]


def load_codex_session_items(session_path):
    path = Path(session_path).expanduser()
    messages = []
    tool_events = []
    turn = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = _message_from_record(record)
            if message:
                turn += 1
                messages.append({
                    "turn": turn,
                    "role": message["role"],
                    "text": redact_text(message["text"]),
                })
                continue
            payload = record.get("payload", {})
            payload_type = str(payload.get("type") or payload.get("name") or "")
            if record.get("type") == "event_msg" or "exec" in payload_type or "tool" in payload_type:
                tool_events.append({
                    "line": line_no,
                    "type": payload_type or record.get("type"),
                })
    return messages, tool_events


def _sparse_sample(items, count):
    if count <= 0 or not items:
        return []
    if len(items) <= count:
        return items
    step = len(items) / (count + 1)
    indexes = [min(len(items) - 1, max(0, round(step * (idx + 1)) - 1)) for idx in range(count)]
    result = []
    seen = set()
    for index in indexes:
        if index not in seen:
            result.append(items[index])
            seen.add(index)
    return result


def probe_codex_session(session_path, head=4, tail=4, sparse=4):
    messages, tool_events = load_codex_session_items(session_path)
    user_count = sum(1 for item in messages if item["role"] == "user")
    assistant_count = sum(1 for item in messages if item["role"] == "assistant")
    return {
        "sessionPath": str(Path(session_path).expanduser()),
        "stats": {
            "messageCount": len(messages),
            "userMessageCount": user_count,
            "assistantMessageCount": assistant_count,
            "toolEventCount": len(tool_events),
        },
        "samples": {
            "head": messages[:head],
            "tail": messages[-tail:] if tail else [],
            "sparse": _sparse_sample(messages[head: max(head, len(messages) - tail)], sparse),
        },
        "toolTimeline": tool_events[:50],
        "recommendedRanges": [],
    }


def slice_codex_session(session_path, ranges):
    messages, _tool_events = load_codex_session_items(session_path)
    slices = []
    for start, end in ranges:
        selected = [item for item in messages if start <= item["turn"] <= end]
        slices.append({"range": [start, end], "messages": selected})
    return slices


def build_analysis_pack(probe, slices):
    lines = [
        "# AIBTI Session Analysis Pack",
        "",
        "## Probe Stats",
        "",
        "```json",
        json.dumps(probe.get("stats", {}), ensure_ascii=False, indent=2),
        "```",
        "",
        "## Analysis Instructions",
        "",
        "- 判断主语始终是“我”（用户）。",
        "- 不使用固定关键词直接判断维度。",
        "- 基于片段语义判断：主导度、信任度、深入度、契合度、甜蜜度。",
        "- 输出时只给 1-5 阶、置信度和抽象理由，不复述隐私内容。",
        "",
    ]
    for item in slices:
        start, end = item["range"]
        lines.extend([f"## Slice {start}-{end}", ""])
        for message in item["messages"]:
            lines.append(f"- T{message['turn']} {message['role']}: {message['text']}")
        lines.append("")
    return "\n".join(lines)


def find_latest_codex_session(codex_home=None):
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    candidates = list((root / "sessions").glob("**/*.jsonl")) + list((root / "archived_sessions").glob("*.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"No Codex session jsonl files found under {root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def fetch_collection_rules(base_url, cache_path):
    url = base_url.rstrip("/") + "/api/config/ai-intimacy?version=latest&locale=zh-CN"
    with urllib.request.urlopen(url, timeout=5) as response:
        rules = json.loads(response.read().decode("utf-8"))
    cache = Path(cache_path)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
    return rules


def load_label_rules(rules_path=None):
    path = Path(rules_path).expanduser() if rules_path else DEFAULT_LABEL_RULES
    return json.loads(path.read_text(encoding="utf-8"))


def _dimension(judge_result, name):
    return (judge_result.get("dimensions") or {}).get(name) or {}


def _dimension_level(judge_result, name):
    value = _dimension(judge_result, name).get("level", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dimension_confidence(judge_result, name):
    value = _dimension(judge_result, name).get("confidence", 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _compare(left, op, right):
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    if op == "==":
        return left == right
    raise ValueError(f"Unsupported label rule operator: {op}")


def _condition_matches(judge_result, condition):
    return _compare(
        _dimension_level(judge_result, condition["dimension"]),
        condition.get("op", ">="),
        int(condition["level"]),
    )


def _rule_dimensions(rule):
    if "all" in rule:
        return [condition["dimension"] for condition in rule["all"]]
    return [rule["dimension"]]


def _rule_matches(judge_result, rule, min_strong_confidence):
    conditions = rule.get("all") or [rule]
    if not all(_condition_matches(judge_result, condition) for condition in conditions):
        return False
    if rule.get("strong"):
        return all(
            _dimension_confidence(judge_result, dimension) >= min_strong_confidence
            for dimension in _rule_dimensions(rule)
        )
    return True


def calculate_labels(judge_result, rules):
    max_tags = int(rules.get("maxTags", 4))
    min_strong_confidence = float(rules.get("minStrongConfidence", 0.55))
    labels = []
    groups = set()

    def add_label(rule):
        label = rule["label"]
        group = rule.get("group", label)
        if label in labels or group in groups or len(labels) >= max_tags:
            return
        labels.append(label)
        groups.add(group)

    for rule in rules.get("combinationRules", []):
        if _rule_matches(judge_result, rule, min_strong_confidence):
            add_label(rule)

    for rule in rules.get("fallbackRules", []):
        if _rule_matches(judge_result, rule, min_strong_confidence):
            add_label(rule)

    return {
        "version": rules.get("version"),
        "locale": rules.get("locale"),
        "labels": labels,
    }


def _bounded_level(judge_result, dimension):
    return max(1, min(5, _dimension_level(judge_result, dimension) or 1))


def _score_band(score):
    if score >= 90:
        return "今日稀有局"
    if score >= 80:
        return "默契上头"
    if score >= 70:
        return "关系成型"
    if score >= 60:
        return "有点感觉"
    return "还在试探"


def calculate_score(judge_result):
    levels = {dimension: _bounded_level(judge_result, dimension) for dimension in DIMENSION_WEIGHTS}
    weighted_level = sum(levels[dimension] * weight for dimension, weight in DIMENSION_WEIGHTS.items())
    score = round(45 + ((weighted_level - 1) / 4) * 50)
    if sum(1 for level in levels.values() if level >= 4) >= 3:
        score += 3
    if sum(1 for level in levels.values() if level <= 2) >= 2:
        score -= 4
    if all(level >= 4 for level in levels.values()):
        score += 2
    return max(45, min(95, score))


def build_components(judge_result):
    components = []
    for dimension, (label, conclusions) in DIMENSION_CONCLUSIONS.items():
        level = _bounded_level(judge_result, dimension)
        components.append({
            "label": label,
            "level": level,
            "conclusion": conclusions[level - 1],
        })
    return components


DAILY_TIP_INTENTS = {
    "dominance": {
        "high": "主导度高时，开玩笑地让 AI 自己浪一下，测试它会不会跑偏。",
        "mid": "主导度中等时，让 AI 先开头，再由我把方向盘抢回来。",
        "low": "主导度低时，反向夺权，下一局直接声明这局听我的。",
    },
    "trust": {
        "high": "信任度高时，让 AI 反过来猜我可能会不满意哪里。",
        "mid": "信任度中等时，给 AI 半张空白卷，看它能不能自己补路。",
        "low": "信任度低时，给 AI 一次免检机会，不急着查作业。",
    },
    "depth": {
        "high": "深入度高时，反向浅聊，只用一句话下命令。",
        "mid": "深入度中等时，追问它为什么这么判断。",
        "low": "深入度低时，往深处戳一下，要求它给依据。",
    },
    "fit": {
        "high": "契合度高时，故意说半句，测试它能不能接住暗号。",
        "mid": "契合度中等时，给 AI 一个小暗号，观察默契会不会自己长出来。",
        "low": "契合度低时，先告诉 AI 我喜欢怎样的回答，帮助对齐暗号。",
    },
    "sweetness": {
        "high": "甜蜜度高时，反向冷脸验货，看 AI 还会不会乖。",
        "mid": "甜蜜度中等时，故意换一种语气，测试它接糖还是接刀。",
        "low": "甜蜜度低时，做对时赏一句糖，但仍保持玩笑感。",
    },
}


DAILY_TIP_PRIORITY = ["dominance", "trust", "depth", "fit", "sweetness"]


def calculate_daily_tips(judge_result):
    levels = {dimension: _bounded_level(judge_result, dimension) for dimension in DIMENSION_WEIGHTS}
    high_dimensions = [dimension for dimension in DAILY_TIP_PRIORITY if levels[dimension] >= 4]
    low_dimensions = [dimension for dimension in DAILY_TIP_PRIORITY if levels[dimension] <= 2]
    if high_dimensions:
        dimension = high_dimensions[0]
    elif low_dimensions:
        dimension = low_dimensions[0]
    else:
        dimension = DAILY_TIP_PRIORITY[0]
    level = levels[dimension]
    bucket = "high" if level >= 4 else "low" if level <= 2 else "mid"
    direction = "reverse-challenge" if bucket == "high" else "reverse-repair" if bucket == "low" else "playful-test"
    return [{
        "dimension": dimension,
        "level": level,
        "direction": direction,
        "intent": DAILY_TIP_INTENTS[dimension][bucket],
    }]


def aibti_code(judge_result):
    axes = judge_result.get("aibtiAxes") or {}
    return "".join(
        AIBTI_AXIS_CODES[axis].get(str(axes.get(axis, "")).lower(), fallback)
        for axis, fallback in [
            ("lead", "F"),
            ("feedback", "T"),
            ("rhythm", "S"),
            ("goal", "D"),
        ]
    )


def model_copywriting_request(source_labels, source_headline, source_components, source_daily_tips, judge_result, card):
    return {
        "mode": "model-polish",
        "locale": card.get("locale"),
        "primaryLanguage": card.get("primaryLanguage"),
        "instructions": [
            "不要暴露工作内容、代码、文件名、项目名、客户信息或原始 prompt。",
            "使用 locale 和 primaryLanguage 对应的本地化语言，不要机械翻译。",
            "基于 sourceLabels 的标签意图生成同类但更有趣味性的展示标签。",
            "基于 sourceHeadline 的原始意图生成同类但更有趣味性的 headline。",
            "基于 sourceComponents 的分量结论意图，生成同类但更有趣味性的 conclusion。",
            "基于 sourceDailyTips 的反向游戏意图，直接生成 1 条有趣味性的 dailyTips；不要照抄 intent，也不要使用预设模板。",
            "保持含义一致，只润色关系味道；不要改变分数、分量 label、level、顺序、aibtiCode 或类型名。",
            "标签最多 4 个，每个标签 4-10 个中文字符；headline 建议 18-34 个中文字符。",
            "components 必须逐项返回原 label，只改 conclusion；每个 conclusion 建议 4-10 个中文字符。",
            "dailyTips 返回数组，默认 1 条，每条建议 18-45 个中文字符。",
            "可以轻微暧昧、控场、嘴硬、撒娇，但避免性、暴力、羞辱和身份刻板印象。",
            "只返回 JSON：{\"labels\":[...],\"headline\":\"...\",\"components\":[{\"label\":\"主导度\",\"conclusion\":\"...\"}],\"dailyTips\":[\"...\"]}。",
        ],
        "sourceLabels": source_labels,
        "sourceHeadline": source_headline,
        "sourceComponents": source_components,
        "sourceDailyTips": source_daily_tips,
        "safeContext": {
            "aibtiCode": card["aibtiCode"],
            "aibtiName": card["aibtiName"],
            "intimacyScore": card["intimacyScore"],
            "scoreBand": card["scoreBand"],
            "components": card["components"],
        },
    }


def compose_card_from_judge(judge_result, label_rules, headline=None):
    labels = calculate_labels(judge_result, label_rules)
    score = calculate_score(judge_result)
    code = aibti_code(judge_result)
    source_labels = labels["labels"]
    source_daily_tips = calculate_daily_tips(judge_result)
    card = {
        "primaryLanguage": judge_result.get("primaryLanguage", "unknown"),
        "locale": judge_result.get("locale") or labels.get("locale"),
        "aibtiCode": code,
        "aibtiName": AIBTI_NAMES.get(code, "AI 关系待命名型"),
        "intimacyScore": score,
        "scoreBand": _score_band(score),
        "components": build_components(judge_result),
        "labels": source_labels,
        "headline": headline,
    }
    card["sourceLabels"] = source_labels
    card["sourceComponents"] = card["components"]
    card["sourceDailyTips"] = source_daily_tips
    if headline is not None:
        card["sourceHeadline"] = headline
    card["copywritingRequest"] = model_copywriting_request(
        source_labels,
        headline,
        card["sourceComponents"],
        card["sourceDailyTips"],
        judge_result,
        card,
    )
    return card


def publish(base_url, payload):
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/posts",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def cleanup_temp_files(temp_dir="/tmp", prefix="aibti-", run_id=None, keep_images=True):
    root = Path(temp_dir).expanduser()
    removed = []
    if not root.exists():
        return removed
    effective_prefix = f"{prefix}{run_id}-" if run_id else prefix
    for path in root.iterdir():
        if not path.is_file() or not path.name.startswith(effective_prefix):
            continue
        if keep_images and path.suffix.lower() in IMAGE_SUFFIXES:
            continue
        if keep_images and path.name.endswith((".png.html", ".jpg.html", ".jpeg.html", ".webp.html")):
            pass
        try:
            path.unlink()
            removed.append(path)
        except FileNotFoundError:
            continue
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI 亲密度特征采集 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record")
    record.add_argument("--log", required=True)
    record.add_argument("--event-json", required=True)

    payload = sub.add_parser("payload")
    payload.add_argument("--log", required=True)
    payload.add_argument("--handle", required=True)
    payload.add_argument("--period-label", default="今日")
    payload.add_argument("--rules-version", default="collection-v1.0.0")

    fetch = sub.add_parser("fetch-rules")
    fetch.add_argument("--base-url", required=True)
    fetch.add_argument("--cache", default=".ai-intimacy/collection-rules-cache.json")

    probe = sub.add_parser("probe-codex-session")
    probe.add_argument("--session")
    probe.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    probe.add_argument("--latest", action="store_true")
    probe.add_argument("--head", type=int, default=4)
    probe.add_argument("--tail", type=int, default=4)
    probe.add_argument("--sparse", type=int, default=4)
    probe.add_argument("--output")

    pack = sub.add_parser("analysis-pack")
    pack.add_argument("--session")
    pack.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    pack.add_argument("--latest", action="store_true")
    pack.add_argument("--ranges", required=True, help="Comma separated turn ranges, e.g. 1-20,80-120")
    pack.add_argument("--output")

    labels = sub.add_parser("calculate-labels")
    labels.add_argument("--judge-json")
    labels.add_argument("--judge-file")
    labels.add_argument("--rules", default=str(DEFAULT_LABEL_RULES))

    card = sub.add_parser("compose-card")
    card.add_argument("--judge-json")
    card.add_argument("--judge-file")
    card.add_argument("--rules", default=str(DEFAULT_LABEL_RULES))
    card.add_argument("--headline")

    post = sub.add_parser("publish")
    post.add_argument("--base-url", required=True)
    post.add_argument("--log", required=True)
    post.add_argument("--handle", required=True)
    post.add_argument("--period-label", default="今日")
    post.add_argument("--rules-version", default="collection-v1.0.0")

    cleanup = sub.add_parser("cleanup-temp")
    cleanup.add_argument("--temp-dir", default="/tmp")
    cleanup.add_argument("--prefix", default="aibti-")
    cleanup.add_argument("--run-id", required=True)
    cleanup.add_argument("--delete-images", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "record":
        record_event(args.log, json.loads(args.event_json))
        print("recorded")
        return 0
    if args.command == "payload":
        print(json.dumps(
            build_payload(args.handle, args.period_label, args.rules_version, load_events(args.log)),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if args.command == "fetch-rules":
        print(json.dumps(fetch_collection_rules(args.base_url, args.cache), ensure_ascii=False, indent=2))
        return 0
    if args.command == "probe-codex-session":
        session = find_latest_codex_session(args.codex_home) if args.latest or not args.session else Path(args.session)
        result = probe_codex_session(session, head=args.head, tail=args.tail, sparse=args.sparse)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    if args.command == "analysis-pack":
        session = find_latest_codex_session(args.codex_home) if args.latest or not args.session else Path(args.session)
        ranges = []
        for item in args.ranges.split(","):
            start, end = item.split("-", 1)
            ranges.append((int(start), int(end)))
        probe = probe_codex_session(session)
        slices = slice_codex_session(session, ranges)
        text = build_analysis_pack(probe, slices)
        if args.output:
            Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    if args.command == "calculate-labels":
        if args.judge_file:
            judge_result = json.loads(Path(args.judge_file).expanduser().read_text(encoding="utf-8"))
        elif args.judge_json:
            judge_result = json.loads(args.judge_json)
        else:
            raise SystemExit("calculate-labels requires --judge-json or --judge-file")
        print(json.dumps(calculate_labels(judge_result, load_label_rules(args.rules)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "compose-card":
        if args.judge_file:
            judge_result = json.loads(Path(args.judge_file).expanduser().read_text(encoding="utf-8"))
        elif args.judge_json:
            judge_result = json.loads(args.judge_json)
        else:
            raise SystemExit("compose-card requires --judge-json or --judge-file")
        print(json.dumps(
            compose_card_from_judge(
                judge_result,
                load_label_rules(args.rules),
                headline=args.headline,
            ),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if args.command == "publish":
        result = publish(
            args.base_url,
            build_payload(args.handle, args.period_label, args.rules_version, load_events(args.log)),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "cleanup-temp":
        removed = cleanup_temp_files(
            args.temp_dir,
            prefix=args.prefix,
            run_id=args.run_id,
            keep_images=not args.delete_images,
        )
        print(json.dumps({
            "removedCount": len(removed),
            "removed": [str(path) for path in removed],
        }, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
