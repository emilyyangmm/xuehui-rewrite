"""
修复 /rewrite 接口 v2：改写不再粗暴压缩原文
用法: python fix_rewrite_v2.py
"""
import re

FILE = "/root/autodl-tmp/main_api.py"

with open(FILE, "r", encoding="utf-8") as f:
    code = f.read()

# ============================================================
# 新的改写专用 prompt 映射（区别于生成用的 SCRIPT_TYPE_PROMPTS）
# 核心区别：保留原文信息量，只改风格和结构
# ============================================================

NEW_BLOCK = '''
# 改写专用脚本风格指引（不同于生成用的 SCRIPT_TYPE_PROMPTS）
# 改写保留原文所有关键信息，只调整表达风格和叙事结构
REWRITE_STYLE_GUIDE = {
    "聊观点": """改写风格：观点输出型
- 用第一人称表达鲜明立场，"我认为""说真的""很多人不知道"
- 开头直接亮观点，中间用原文中的案例和数据支撑
- 结尾抛出争议性问题引导评论
- 语气有个性、有态度，可以略带偏激""",

    "晒过程": """改写风格：过程记录型
- 按时间顺序重新组织内容，像在跟朋友聊天
- 保留所有操作细节和步骤，加入真实感受
- 突出遇到的困难和解决方法
- 语气自然真实，有现场感""",

    "教知识": """改写风格：知识教学型
- 用"我来教你""跟着我做"等教学口吻
- 保留原文所有知识点和步骤，按逻辑重新排列
- 把专业术语用大白话解释一遍
- 复杂内容分段讲解，每段一个知识点，不要强行压缩""",

    "讲故事": """改写风格：故事叙述型
- 用叙事手法重新组织，制造悬念和转折
- 用对话和细节让内容生动
- 按"起因→经过→高潮→结局"重构
- 让读者有代入感，像在听故事""",

    "尬段子": """改写风格：幽默吐槽型
- 用自嘲和夸张的方式重新表达
- 在关键节点加入意想不到的转折和笑点
- 语气轻松搞笑，多用网络梗
- 保留核心信息但用段子手法包装""",

    "说产品": """改写风格：种草带货型
- 从使用者角度描述体验
- 突出产品解决了什么问题，效果如何
- 加入真实使用感受，可以提小缺点显得真实
- 结尾给出明确建议""",

    "做测评": """改写风格：客观测评型
- 用测评博主的口吻，强调客观对比
- 列出优缺点，引用具体数据
- 给不同人群不同建议
- 语气专业但不枯燥""",

    "揭内幕": """改写风格：揭秘爆料型
- 开头用震惊体吊胃口，"很多人不知道的是..."
- 把原文中的专业知识包装成"内幕""秘密"
- 语气有紧迫感，像在悄悄告诉你
- 结尾告诉观众如何利用这个信息""",

    "做挑战": """改写风格：挑战记录型
- 设定一个明确的挑战目标
- 描述过程中的紧张和意外
- 突出困难和突破的瞬间
- 结尾揭示结果，语气有期待感""",

    "做采访": """改写风格：采访对话型
- 用问答形式重新组织内容
- 把关键信息变成精彩的回答
- 加入采访者的反应和点评
- 语气轻松，有现场互动感""",

    "拍日常": """改写风格：日常生活型
- 用生活化的口吻，像写日记一样
- 加入生活小细节和个人感受
- 语气温暖自然，不要太正式
- 结尾分享一句心得感悟""",

    "秀蜕变": """改写风格：前后对比型
- 重点突出变化前的状态和变化后的效果
- 中间详细说明做了什么改变
- 用具体数据和细节增强对比感
- 语气励志，激励观众""",

    "搞辩论": """改写风格：辩论对抗型
- 把内容中的不同观点提取出来对立呈现
- 正反方都给出有力论据
- 表达自己的立场
- 结尾让观众站队""",

    "列清单": """改写风格：清单盘点型
- 把原文核心内容提炼为编号清单
- 每条清单有标题+简要说明
- 按重要程度排序
- 信息密度高，适合收藏""",

    "看反应": """改写风格：反应记录型
- 用旁观者视角描述过程和反应
- 突出意外和出乎意料的部分
- 加入情绪描写
- 语气轻松幽默""",

    "答粉丝": """改写风格：粉丝问答型
- 把内容转化为回答粉丝提问的形式
- 语气亲切真诚，像回复朋友
- 结合自己经历举例说明
- 鼓励互动提问""",

    "搞联动": """改写风格：联动互动型
- 体现不同视角的碰撞和互补
- 描述合作过程中的有趣瞬间
- 语气有互动感和化学反应
- 突出1+1>2的效果""",

    "幕后花絮": """改写风格：幕后揭秘型
- 把内容包装成"你不知道的幕后"
- 展示真实的制作过程，包括失误和意外
- 语气真实不做作
- 让观众看到平时看不到的一面""",

    "造热点": """改写风格：热点解读型
- 开头关联当下热点
- 用独特角度解读原文内容
- 提供增量信息，不只是蹭热度
- 语气要快，有时效感""",

    "打鸡血": """改写风格：励志激励型
- 用短句和有力量的表达
- 把原文中的成果和方法包装成励志故事
- 传递"你也可以做到"的信念
- 结尾一句话总结，适合截图转发""",
}

'''

# ============================================================
# 新的 /rewrite 接口
# ============================================================

NEW_REWRITE = r'''@app.post("/rewrite")
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

    # 构建系统 prompt
    if system:
        style_prompt = system
    elif script_type and script_type in REWRITE_STYLE_GUIDE:
        style_guide = REWRITE_STYLE_GUIDE[script_type]
        style_prompt = f"""你是一位专业的短视频口播文案改写专家。

【任务】将用户提供的原始文案改写为抖音风格的口播文案。

【核心原则】
1. 保留原文的所有关键信息、知识点、步骤和案例，不要丢失内容
2. 改写是重新组织和润色，不是缩写或概括
3. 改写后的字数应与原文相当，不要大幅压缩
4. 按照下方的脚本风格进行改写

{style_guide}

【语言要求】
- 口语化，适合TTS朗读，像在跟朋友聊天
- 多用短句，避免书面语和专业术语
- 自然加入语气词（嗯、对吧、你想想、说真的）
- 结尾加一句行动号召（关注/收藏/评论）

【输出要求】
- 直接输出改写后的完整文案
- 不要加任何说明、标题、分段标记
- 不要输出"改写后："等前缀"""
    else:
        style_prompt = XUE_SYSTEM_PROMPT

    # 融入爆款元素
    viral_hint = ""
    if viral_elements:
        if isinstance(viral_elements, str):
            viral_elements = [e.strip() for e in viral_elements.split(",") if e.strip()]
        descs = [VIRAL_ELEMENT_MAP.get(e, e) for e in viral_elements if e]
        if descs:
            viral_hint = "\n\n【融入以下爆款元素的表达方式】\n" + "\n".join(descs) + "\n在改写中自然融入这些元素的钩子词和表达风格，不要生硬堆砌。"

    user_content = f"请将以下文案按照指定风格进行改写，保留所有核心内容和关键信息：{viral_hint}\n\n{text}"
    result = call_qwen(style_prompt, user_content, api_key)
    return JSONResponse({"result": result})'''


# ============================================================
# 执行替换
# ============================================================

# 1. 插入 REWRITE_STYLE_GUIDE（在 VIRAL_ELEMENT_MAP 后面）
if "REWRITE_STYLE_GUIDE" not in code:
    # 找到 VIRAL_ELEMENT_MAP 结尾
    map_pattern = r'(VIRAL_ELEMENT_MAP = \{.*?\}\s*\n)'
    map_match = re.search(map_pattern, code, re.DOTALL)
    if map_match:
        insert_pos = map_match.end()
        code = code[:insert_pos] + NEW_BLOCK + code[insert_pos:]
        print("✅ 已插入 REWRITE_STYLE_GUIDE")
    else:
        # 如果没有 VIRAL_ELEMENT_MAP，在 /rewrite 前插入
        rw_pos = code.find('@app.post("/rewrite")')
        if rw_pos > 0:
            code = code[:rw_pos] + NEW_BLOCK + code[rw_pos:]
            print("✅ 已插入 REWRITE_STYLE_GUIDE（在 /rewrite 前）")
        else:
            print("❌ 找不到插入位置")
            exit(1)
else:
    print("⏭️  REWRITE_STYLE_GUIDE 已存在，跳过插入")

# 2. 替换 /rewrite 接口
pattern = r'@app\.post\("/rewrite"\)\nasync def rewrite\(.*?\n    return JSONResponse\(\{"result": result\}\)'
match = re.search(pattern, code, re.DOTALL)
if match:
    code = code[:match.start()] + NEW_REWRITE + code[match.end():]
    print("✅ 已替换 /rewrite 接口")
else:
    print("❌ 没找到 /rewrite 接口")
    exit(1)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(code)

print("\n🎉 全部完成！请重启服务: pkill -f main_api.py; sleep 1; cd /root/autodl-tmp && nohup python main_api.py > /tmp/api.log 2>&1 &")
