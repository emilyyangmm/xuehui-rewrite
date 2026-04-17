"""
修复 main_api.py 的 /rewrite 接口
用法: python fix_rewrite.py
"""
import re

FILE = "/root/autodl-tmp/main_api.py"

with open(FILE, "r", encoding="utf-8") as f:
    code = f.read()

# === 1. 要插入的爆款元素映射 ===
MAP = '''VIRAL_ELEMENT_MAP = {
    "cost": "成本：花小钱办大事，省钱省时省力，性价比拉满",
    "crowd": "人群：锁定特定群体，用身份标签引发共鸣",
    "curiosity": "猎奇：反常识、冷知识、揭秘，制造悬念",
    "contrast": "反差：强烈对比和转折，意想不到",
    "worst": "最差：负面情绪引流，避坑、吐槽",
    "authority": "头牌：借势权威大牌，明星同款",
    "nostalgia": "怀旧：激活集体记忆，童年回忆",
    "hormone": "荷尔蒙：情感社交话题，脱单、前任",
}

'''

# === 2. 新的 /rewrite 接口 ===
NEW = r'''@app.post("/rewrite")
async def rewrite(request: Request, text: str = Form(None), system: str = Form(default=""), script_type: str = Form(default=""), viral_elements: str = Form(default="")):
    if text is None:
        body = await request.body()
        try:
            data = json.loads(body)
            text = data.get("text", "")
            system = data.get("system", "")
            script_type = data.get("script_type", "")
            viral_elements = data.get("viral_elements", [])
        except Exception:
            return JSONResponse({"error": "缺少text参数"}, status_code=400)
    api_key = get_qwen_key(request)

    # 优先用脚本类型专属prompt，不再千篇一律用XUE_SYSTEM_PROMPT
    if system:
        style_prompt = system
    elif script_type and script_type in SCRIPT_TYPE_PROMPTS:
        type_prompt = SCRIPT_TYPE_PROMPTS[script_type]
        style_prompt = type_prompt + "\n\n语言风格要求：\n- 口语化、有节奏感，适合TTS朗读\n- 多用短句，每句不超过20字\n- 禁止用书面语和专业术语\n- 控制在300-500字之间\n- 直接输出改写后的文案，不要加任何说明"
    else:
        style_prompt = XUE_SYSTEM_PROMPT

    # 融入爆款元素
    viral_hint = ""
    if viral_elements:
        if isinstance(viral_elements, str):
            viral_elements = [e.strip() for e in viral_elements.split(",") if e.strip()]
        descs = [VIRAL_ELEMENT_MAP.get(e, e) for e in viral_elements if e]
        if descs:
            viral_hint = "\n\n【必须融入的爆款元素】\n" + "\n".join(descs) + "\n请自然融入以上元素的表达方式，不要生硬堆砌。"

    user_content = f"请判断以下文案的行业方向，严格按该行业改写，不能跑题。{viral_hint}\n\n原文：\n{text}"
    result = call_qwen(style_prompt, user_content, api_key)
    return JSONResponse({"result": result})'''

# === 3. 执行替换 ===
pattern = r'@app\.post\("/rewrite"\)\nasync def rewrite\(.*?\n    return JSONResponse\(\{"result": result\}\)'
match = re.search(pattern, code, re.DOTALL)

if match:
    code = code[:match.start()] + MAP + NEW + code[match.end():]
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(code)
    print("✅ 替换成功！请重启服务。")
else:
    print("❌ 没找到旧的 /rewrite 接口，可能已经改过了。")
