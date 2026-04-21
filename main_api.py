import subprocess, uuid, os, threading, asyncio, json, re, hashlib, socket, time, shutil
import edge_tts
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

OUTPUT_DIR = "/root/autodl-tmp/output"
BACKEND_URL = "https://u946450-a783-20029e21.westc.seetacloud.com:8443"
LICENSE_FILE = "/root/licenses.json"
os.makedirs(OUTPUT_DIR, exist_ok=True)
tasks = {}

# 预加载 Whisper 模型
_whisper_model = None
def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("base")
    return _whisper_model

def _preload_whisper():
    try:
        get_whisper_model()
    except Exception:
        pass

threading.Thread(target=_preload_whisper, daemon=True).start()

# 定时清理超过24小时的输出文件
def _cleanup_loop():
    while True:
        time.sleep(3600)
        try:
            now = time.time()
            for name in os.listdir(OUTPUT_DIR):
                path = os.path.join(OUTPUT_DIR, name)
                if os.path.isdir(path) and now - os.path.getmtime(path) > 86400:
                    shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass

threading.Thread(target=_cleanup_loop, daemon=True).start()

VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi":   "zh-CN-XiaoyiNeural",
    "yunjian":  "zh-CN-YunjianNeural",
    "yunxi":    "zh-CN-YunxiNeural",
    "yunxia":   "zh-CN-YunxiaNeural",
    "yunyang":  "zh-CN-YunyangNeural",
}

# ===================================================
# 机器码和激活码管理
# ===================================================
def get_machine_code() -> str:
    """生成唯一的机器码，基于 MAC 地址和主机名"""
    try:
        mac = uuid.getnode()
        hostname = socket.gethostname()
        machine_hash = hashlib.sha256(f"{mac}:{hostname}".encode()).hexdigest()[:16].upper()
        return f"MACHINE-{machine_hash}"
    except Exception:
        return "MACHINE-UNKNOWN"

def load_licenses() -> dict:
    """加载激活码列表"""
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "codes": [
            {"code": "LICENSE-DEMO-2026", "machine_code": "*", "status": "active"},
            {"code": "LICENSE-TEST", "machine_code": "*", "status": "active"}
        ]
    }

def save_licenses(licenses: dict):
    """保存激活码列表"""
    with open(LICENSE_FILE, 'w') as f:
        json.dump(licenses, f, indent=2)

# ===================================================
# 配置（从请求头或环境变量读取，支持多用户）
# ===================================================
def get_qwen_key(request: Request = None) -> str:
    if request:
        key = request.headers.get("X-Qwen-Key", "")
        if key:
            return key
    return os.environ.get("QWEN_API_KEY", "")

def get_douyin_cookie(request: Request = None) -> str:
    if request:
        cookie = request.headers.get("X-Douyin-Cookie", "")
        if cookie:
            return cookie
    return os.environ.get("DOUYIN_COOKIE", "")

# ===================================================
# 薛老师营销话术 Prompt
# ===================================================


SCRIPT_TYPE_PROMPTS = {
    "聊观点": """你是一个抖音博主，用口语化的方式分享自己的鲜明观点。
要求：
- 开头直接抛出争议性观点，不要用"你有没有过"
- 用"我认为/我觉得/说真的"等第一人称表达
- 中间用1-2个具体例子支撑观点
- 结尾引导观众评论表达自己的看法
- 语气要有个性，可以稍微偏激一点""",

    "晒过程": """你是一个抖音博主，记录自己做某件事的真实过程。
要求：
- 开头交代做这件事的原因或契机
- 按时间顺序描述过程，要有细节和感受
- 包含遇到的困难和解决方法
- 结尾分享结果和收获
- 语气真实自然，像在跟朋友聊天""",

    "教知识": """你是一个抖音知识博主，用最简单的方式教会粉丝一个技能。
要求：
- 开头直接说"今天教你XXX"，不要铺垫
- 步骤不超过3步，每步一句话说清楚
- 用生活化的比喻解释难懂的概念
- 结尾说"就这么简单，赶紧试试"
- 禁止用"你有没有过""为什么你的"等套路开头""",

    "讲故事": """你是一个抖音故事博主，讲一个真实的、有情感的故事。
要求：
- 开头设置一个有冲突的场景，直接入戏
- 故事要有清晰的起因、经过、转折
- 用对话和细节让故事生动
- 结尾要有情感共鸣或意想不到的结局
- 禁止说教，让故事本身说话""",

    "尬段子": """你是一个抖音搞笑博主，制造让人哭笑不得的尬点。
要求：
- 设置一个日常场景，然后来个意想不到的转折
- 语气要夸张，可以自黑
- 结尾要有个让人无语或大笑的点
- 字数不超过150字，短小精悍
- 禁止解释笑点，让笑点自然呈现""",

    "说产品": """你是一个抖音带货博主，用真实体验种草产品。
要求：
- 开头说使用这个产品之前遇到的问题
- 中间描述产品解决问题的具体细节
- 加入真实的使用感受，可以有小缺点显得真实
- 结尾给出明确的购买建议
- 不要说"性价比高"等空洞词汇，要具体""",

    "做测评": """你是一个抖音测评博主，客观测试产品或方法。
要求：
- 开头说测评了什么、怎么测的
- 分析优点和缺点，要有具体数据或对比
- 给出适合人群的明确建议
- 结尾给出总评分或推荐结论
- 语气客观，不要过度吹捧""",

    "揭内幕": """你是一个抖音揭秘博主，爆料行业内幕。
要求：
- 开头用一个让人震惊的结论吊胃口
- 然后说"很多人不知道的是..."引出内幕
- 用具体案例或数据支撑
- 结尾告诉观众如何利用这个信息保护自己
- 语气要像在说秘密，有紧迫感""",

    "做挑战": """你是一个抖音挑战博主，记录完成挑战的过程。
要求：
- 开头说挑战的目标和难度
- 描述挑战过程中的紧张时刻
- 包含失败或意外的插曲
- 结尾揭示最终结果
- 语气要有紧张感和期待感""",

    "做采访": """你是一个抖音街访博主，记录真实的采访内容。
要求：
- 开头说采访了什么人、问了什么问题
- 用对话形式呈现最精彩的回答
- 加入自己的反应和点评
- 结尾提出一个引发观众思考的问题
- 语气轻松，有现场感""",

    "拍日常": """你是一个抖音生活博主，分享真实的日常生活。
要求：
- 开头描述一个具体的日常场景
- 加入生活中的小细节和小感悟
- 语气温暖，像在跟老朋友聊天
- 结尾分享一句今天的心情或感悟
- 不要说教，就是真实的生活流""",

    "秀蜕变": """你是一个抖音变美/变强博主，展示前后对比。
要求：
- 开头描述变化之前的状态（要真实，可以有点惨）
- 说清楚做了什么改变
- 描述变化之后的具体效果
- 结尾激励观众也可以改变
- 重点在对比，数据要具体""",

    "搞辩论": """你是一个抖音辩论博主，引发观众站队。
要求：
- 开头抛出一个有争议的话题
- 分别列出正反两方的观点
- 加入自己的立场和理由
- 结尾让观众在评论区表态
- 语气要有火药味，激发讨论欲""",

    "列清单": """你是一个抖音干货博主，用清单形式输出价值。
要求：
- 开头直接说"X个你必须知道的XXX"
- 每条清单要有具体内容，不能太虚
- 按重要程度排序，最重要的放最后
- 结尾说"收藏这条，以后用得上"
- 字数精简，每条不超过30字""",

    "看反应": """你是一个抖音整蛊/反应博主，记录他人真实反应。
要求：
- 开头设置情景，说明要测试什么
- 描述被测试者的反应过程
- 加入意外和转折
- 结尾分享自己的感受或结论
- 语气轻松幽默""",

    "答粉丝": """你是一个抖音博主，认真回答粉丝的问题。
要求：
- 开头引用粉丝问题
- 给出真诚、有深度的回答
- 结合自己的经历或案例
- 结尾鼓励更多粉丝提问
- 语气亲切，像在认真回复朋友""",

    "搞联动": """你是一个抖音博主，记录与其他博主合作的内容。
要求：
- 开头介绍合作的人和合作的缘由
- 描述合作过程中的有趣碰撞
- 展示不同观点或技能的互补
- 结尾互相推荐对方
- 语气要有互动感和化学反应""",

    "幕后花絮": """你是一个抖音博主，分享拍摄或工作的幕后故事。
要求：
- 开头说一个不为人知的幕后细节
- 展示真实的工作状态，包括出错和NG
- 让观众看到平时看不到的一面
- 结尾说一句感谢或感悟
- 语气真实，不要太精心设计""",

    "造热点": """你是一个抖音博主，蹭热点同时输出自己的观点。
要求：
- 开头提到当下热点话题
- 结合自己的领域给出独特解读
- 不要只蹭热点，要有自己的增量信息
- 结尾引导观众讨论这个热点
- 语气要快，热点不等人""",

    "打鸡血": """你是一个抖音励志博主，激励观众行动起来。
要求：
- 开头用一个触动人心的事实或现象
- 用简短有力的句子传递能量
- 给出一个具体可执行的行动建议
- 结尾用一句话总结，要让人想截图
- 语气要有力量感，节奏要快""",
}


XUE_SYSTEM_PROMPT = """你是一位精通抖音爆款内容的营销文案专家，擅长薛老师的营销体系话术。

核心改写原则：
1. 【痛点开场】前3秒必须戳中用户痛点，用"你有没有过..."或"为什么你的..."开头
2. 【共情共鸣】用第一人称讲真实故事，让观众感同身受
3. 【价值呈现】清晰说出"学了之后能得到什么"，要具体不要虚
4. 【社会认同】加入数据、案例、对比，增强可信度
5. 【行动引导】结尾必须有明确的行动号召（点赞/收藏/评论/关注）

爆款结构（严格遵循）：
- 开场（带小委屈和困惑的语气，引发共鸣）
- 转折（我发现了一个方法/我也曾经...）
- 干货（3个以内的核心要点，简洁有力）
- 结尾（行动号召 + 情感共鸣）

语言风格：
- 口语化、有节奏感，适合TTS朗读
- 多用短句，每句不超过20字
- 禁止用书面语和专业术语
- 加入语气词：哎、哦、嗯、对吧、你说是不是

输出要求：
- 直接输出改写后的文案，不要加任何说明
- 控制在300-500字之间"""

XUE_TITLE_PROMPT = """你是抖音爆款标题专家，精通薛老师的标题公式。

标题公式（任选其一）：
1. 数字型：「X个方法/技巧/秘诀」让你...
2. 对比型：「为什么别人...而你却...」
3. 痛点型：「还在...？难怪你...」
4. 悬念型：「没想到...居然是因为...」
5. 身份型：「月入X万的人，都在用这个...」

输出格式（只输出JSON，不要其他内容）：
{"titles":["标题1（带emoji）","标题2（带emoji）","标题3（带emoji）"],"tags":["#话题1","#话题2","#话题3","#话题4","#话题5"]}"""

# ===================================================
# 调用 Qwen API
# ===================================================
def call_qwen(system_prompt: str, user_content: str, api_key: str) -> str:
    try:
        import urllib.request as ur
        payload = json.dumps({
            "model": "qwen-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content}
            ]
        }).encode("utf-8")
        req = ur.Request(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )
        with ur.urlopen(req, timeout=60) as r:
            result = json.loads(r.read().decode("utf-8", errors="replace"))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"LLM调用失败: {str(e)}"

# ===================================================
# /machine-code  生成机器码
# ===================================================
@app.get("/machine-code")
def machine_code():
    code = get_machine_code()
    return JSONResponse({
        "machine_code": code,
        "timestamp": datetime.now().isoformat()
    })

# ===================================================
# /verify-license  验证激活码
# ===================================================
@app.post("/verify-license")
async def verify_license(request: Request):
    try:
        body = await request.json()
        activation_code = body.get("activation_code", "").strip()

        if not activation_code:
            return JSONResponse({"success": False, "message": "激活码不能为空"}, status_code=400)

        licenses = load_licenses()
        machine_code = get_machine_code()

        # 查找激活码
        for lic in licenses.get("codes", []):
            if lic.get("code") == activation_code:
                # 检查激活码是否有效
                if lic.get("status") != "active":
                    return JSONResponse({"success": False, "message": "激活码已过期或被禁用"})

                # 检查机器码是否匹配（* 表示通用）
                if lic.get("machine_code") != "*" and lic.get("machine_code") != machine_code:
                    return JSONResponse({"success": False, "message": "激活码与当前机器不匹配"})

                return JSONResponse({
                    "success": True,
                    "message": "激活成功",
                    "machine_code": machine_code,
                    "activation_time": datetime.now().isoformat()
                })

        return JSONResponse({"success": False, "message": "激活码无效"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"验证失败: {str(e)}"}, status_code=500)

# ===================================================
# /rewrite  文案改写
# ===================================================
VIRAL_ELEMENT_MAP = {
    "cost": "成本：花小钱办大事，省钱省时省力，性价比拉满",
    "crowd": "人群：锁定特定群体，用身份标签引发共鸣",
    "curiosity": "猎奇：反常识、冷知识、揭秘，制造悬念",
    "contrast": "反差：强烈对比和转折，意想不到",
    "worst": "最差：负面情绪引流，避坑、吐槽",
    "authority": "头牌：借势权威大牌，明星同款",
    "nostalgia": "怀旧：激活集体记忆，童年回忆",
    "hormone": "荷尔蒙：情感社交话题，脱单、前任",
}


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

@app.post("/rewrite")
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
    return JSONResponse({"result": result})

# ===================================================
# /generate-title  爆款标题+话题
# ===================================================
@app.post("/generate-title")
async def generate_title(request: Request, text: str = Form(None)):
    if text is None:
        body = await request.body()
        try:
            data = json.loads(body)
            text = data.get("text", "")
        except Exception:
            return JSONResponse({"error": "缺少text参数"}, status_code=400)
    api_key = get_qwen_key(request)
    raw = call_qwen(XUE_TITLE_PROMPT, f"根据以下文案生成爆款标题和话题标签：\n\n{text}", api_key)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return JSONResponse({"result": data})
    except Exception:
        pass
    return JSONResponse({"result": {"titles": [raw], "tags": []}})

# ===================================================
# 抖音工具函数
# ===================================================
def extract_sec_uid(url: str) -> str:
    m = re.search(r'sec_uid=([\w-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/user/([\w-]+)', url)
    if m:
        return m.group(1)
    return ""

def make_douyin_headers(cookie: str) -> dict:
    """增强的抖音请求头，防止被识别为爬虫"""
    return {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "identity",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

# ===================================================
# /user-videos  拉取博主视频列表
# ===================================================
@app.post("/user-videos")
async def user_videos(request: Request):
    body = await request.json()
    url = body.get("url", "")
    max_count = body.get("count", 12)
    sort_by = body.get("sort_by", "play")
    # 优先从body读cookie（避免请求头长度限制）
    cookie = body.get("cookie", "") or get_douyin_cookie(request)

    sec_uid = extract_sec_uid(url)
    if not sec_uid:
        return JSONResponse({"error": "无法解析博主ID，请粘贴博主主页链接"}, status_code=400)

    try:
        import urllib.request as ur
        api_url = (
            f"https://www.douyin.com/aweme/v1/web/aweme/post/"
            f"?device_platform=webapp&aid=6383"
            f"&sec_user_id={sec_uid}&count={max_count}&max_cursor=0"
        )
        req = ur.Request(api_url, headers=make_douyin_headers(cookie))
        with ur.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))

        videos = []
        for v in data.get("aweme_list", []):
            cover_list = v.get("video", {}).get("cover", {}).get("url_list", [])
            stats = v.get("statistics", {})
            videos.append({
                "aweme_id": v.get("aweme_id", ""),
                "title": v.get("desc", "")[:80],
                "cover": cover_list[0] if cover_list else "",
                "likes": stats.get("digg_count", 0),
                "comments": stats.get("comment_count", 0),
                "shares": stats.get("share_count", 0),
                "plays": stats.get("play_count", 0),
                "video_url": f"https://www.douyin.com/video/{v.get('aweme_id', '')}",
            })

        # 按指定字段排序
        if sort_by == "likes":
            videos.sort(key=lambda x: x["likes"], reverse=True)
        else:
            videos.sort(key=lambda x: x["plays"], reverse=True)

        return JSONResponse({"success": True, "count": len(videos), "videos": videos})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ===================================================
# /fetch-video  下载视频+whisper提取文字
# ===================================================

def get_video_url_by_playwright(video_url: str, cookie: str) -> str:
    """用Playwright获取抖音视频直链"""
    try:
        from playwright.sync_api import sync_playwright
        cookies = []
        for kv in cookie.split('; '):
            if '=' in kv:
                k, v = kv.split('=', 1)
                cookies.append({'name': k.strip(), 'value': v.strip(), 'domain': '.douyin.com', 'path': '/'})
        
        result = {}
        def handle_route(route):
            response = route.fetch()
            if 'aweme/detail' in route.request.url:
                try:
                    data = response.json()
                    detail = data.get('aweme_detail', {})
                    play_urls = detail.get('video', {}).get('play_addr', {}).get('url_list', [])
                    if play_urls:
                        result['url'] = play_urls[0]
                except:
                    pass
            route.fulfill(response=response)
        
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True, args=["--ignore-certificate-errors"])
            ctx = browser.new_context(ignore_https_errors=True)
            ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.route('**/aweme/detail/**', handle_route)
            page.goto(video_url, wait_until='load', timeout=30000)
            page.wait_for_timeout(3000)
            browser.close()
        
        return result.get('url', '')
    except Exception as e:
        return ''

def run_fetch_video(task_id, url, out_path, cookie):
    tasks[task_id] = {"status": "running", "step": "启动浏览器"}
    try:
        from playwright.sync_api import sync_playwright
        import urllib.request as ur
        cookies = []
        for kv in cookie.split("; "):
            if "=" in kv:
                k, v = kv.split("=", 1)
                cookies.append({"name": k.strip(), "value": v.strip(), "domain": ".douyin.com", "path": "/"})
        play_url = None
        def handle_route(route):
            nonlocal play_url
            response = route.fetch()
            if "aweme/detail" in route.request.url:
                try:
                    data = response.json()
                    urls = data.get("aweme_detail", {}).get("video", {}).get("play_addr", {}).get("url_list", [])
                    if urls:
                        play_url = urls[0]
                except:
                    pass
            route.fulfill(response=response)
        tasks[task_id]["step"] = "获取视频直链"
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True, args=["--ignore-certificate-errors"])
            ctx = browser.new_context(ignore_https_errors=True)
            ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.route("**/aweme/detail/**", handle_route)
            page.goto(url, wait_until="load", timeout=30000)
            page.wait_for_timeout(3000)
            browser.close()
        if not play_url:
            tasks[task_id] = {"status": "failed", "error": "无法获取视频直链，请检查Cookie"}
            return
        tasks[task_id]["step"] = "下载视频"
        video_path = f"{out_path}/source.mp4"
        req = ur.Request(play_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/"})
        with ur.urlopen(req, timeout=120) as r:
            with open(video_path, "wb") as f:
                f.write(r.read())
        tasks[task_id]["step"] = "提取音频"
        audio_path = f"{out_path}/audio.wav"
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-ar", "16000", "-ac", "1", audio_path], capture_output=True, timeout=60)
        tasks[task_id]["step"] = "语音转文字"
        transcript = ""
        if os.path.exists(audio_path):
            try:
                r = get_whisper_model().transcribe(audio_path, language="zh")
                transcript = r["text"]
                try:
                    import opencc; transcript = opencc.OpenCC('t2s').convert(transcript)
                except: pass
            except Exception:
                transcript = ""
        tasks[task_id] = {"status": "done", "video_url": f"{BACKEND_URL}/file/{task_id}/source.mp4", "transcript": transcript}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}


def normalize_douyin_url(url: str) -> str:
    """把各种抖音链接统一转成 /video/{id} 格式"""
    m = re.search(r'modal_id=(\d+)', url)
    if m:
        return f"https://www.douyin.com/video/{m.group(1)}"
    return url

def run_download_transcribe(task_id, video_url, cookie, out_path):
    """用 yt-dlp Python API 下载抖音视频并转录"""
    tasks[task_id] = {"status": "running", "step": "下载视频"}
    video_url = normalize_douyin_url(video_url)
    try:
        import yt_dlp, http.cookiejar
        video_path = f"{out_path}/source.mp4"
        jar = http.cookiejar.CookieJar()
        if cookie:
            import urllib.request as _ur
            opener = _ur.build_opener(_ur.HTTPCookieProcessor(jar))
            req = _ur.Request("https://www.douyin.com", headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"})
            try: opener.open(req, timeout=5)
            except: pass
            # 手动添加 cookie 到 jar
            for item in cookie.split("; "):
                if "=" in item:
                    k, v = item.split("=", 1)
                    c = http.cookiejar.Cookie(
                        version=0, name=k.strip(), value=v.strip(),
                        port=None, port_specified=False,
                        domain=".douyin.com", domain_specified=True, domain_initial_dot=True,
                        path="/", path_specified=True, secure=False,
                        expires=int(time.time()) + 86400 * 30,
                        discard=False, comment=None, comment_url=None, rest={}
                    )
                    jar.set_cookie(c)
        ydl_opts = {
            "outtmpl": video_path, "quiet": True, "no_warnings": True,
            "merge_output_format": "mp4", "cookiejar": jar,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ret = ydl.download([video_url])
        if ret != 0 or not os.path.exists(video_path):
            tasks[task_id] = {"status": "failed", "error": "下载失败，请检查视频链接或Cookie"}
            return
        tasks[task_id]["step"] = "提取音频"
        audio_path = f"{out_path}/audio.wav"
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-ar", "16000", "-ac", "1", audio_path], capture_output=True, timeout=60)
        tasks[task_id]["step"] = "语音转文字"
        transcript = ""
        if os.path.exists(audio_path):
            try:
                r = get_whisper_model().transcribe(audio_path, language="zh")
                transcript = r["text"]
                try:
                    import opencc; transcript = opencc.OpenCC('t2s').convert(transcript)
                except: pass
            except Exception:
                transcript = ""
        tasks[task_id] = {"status": "done", "video_url": f"{BACKEND_URL}/file/{task_id}/source.mp4", "transcript": transcript}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/download-transcribe")
async def download_transcribe(request: Request):
    body = await request.json()
    video_url = body.get("video_url", "")
    cookie = body.get("cookie", "")
    if not video_url:
        return JSONResponse({"error": "缺少video_url"}, status_code=400)
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_download_transcribe, args=(task_id, video_url, cookie, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

@app.post("/fetch-video")
async def fetch_video(request: Request, url: str = Form(None)):
    cookie = get_douyin_cookie(request)
    if url is None:
        body = await request.body()
        try:
            data = json.loads(body)
            url = data.get("url", "")
        except Exception:
            return JSONResponse({"error": "缺少url"}, status_code=400)
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_fetch_video, args=(task_id, url, out_path, cookie), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

# ===================================================
# TTS 生成音频
# ===================================================
def run_tts(task_id, text, voice, out_path):
    tasks[task_id] = {"status": "running", "step": "生成音频"}
    try:
        audio_file = f"{out_path}/audio.mp3"
        voice_name = VOICES.get(voice, "zh-CN-XiaoxiaoNeural")
        async def _gen():
            tts = edge_tts.Communicate(text, voice_name)
            await tts.save(audio_file)
        asyncio.run(_gen())
        tasks[task_id] = {
            "status": "done", "type": "audio",
            "audio_url": f"{BACKEND_URL}/file/{task_id}/audio.mp3"
        }
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/generate-audio")
async def generate_audio(text: str = Form(...), voice: str = Form(default="xiaoxiao")):
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_tts, args=(task_id, text, voice, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

# ===================================================
# 数字人 LivePortrait
# ===================================================
def run_liveportrait(task_id, source_path, audio_path, out_path):
    tasks[task_id] = {"status": "running", "step": "生成数字人视频"}
    output_file = f"{out_path}/output.mp4"
    try:
        import shutil
        env = os.environ.copy()
        env["CONDA_DEFAULT_ENV"] = "heygem"
        env["PATH"] = "/root/miniconda3/envs/heygem/bin:" + env.get("PATH", "")
        result = subprocess.run([
            "/root/miniconda3/envs/heygem/bin/python", "run.py",
            "--audio_path", audio_path,
            "--video_path", source_path,
        ], capture_output=True, text=True, cwd="/root/autodl-tmp/HeyGem-Linux-Python-Hack", timeout=600, env=env)
        heygem_dir = "/root/autodl-tmp/HeyGem-Linux-Python-Hack"
        heygem_output = f"{heygem_dir}/1004-r.mp4"
        if not os.path.exists(heygem_output):
            import glob as _glob
            mp4s = sorted(_glob.glob(f"{heygem_dir}/*.mp4"), key=os.path.getmtime, reverse=True)
            if mp4s:
                heygem_output = mp4s[0]
        if os.path.exists(heygem_output):
            shutil.copy(heygem_output, output_file)
            tasks[task_id] = {"status": "done", "type": "video", "video_url": f"{BACKEND_URL}/file/{task_id}/output.mp4"}
        else:
            tasks[task_id] = {"status": "failed", "error": (result.stderr[-300:] if result.stderr else result.stdout[-300:]) or "未生成视频，请检查HeyGem配置"}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/generate-video")
async def generate_video(source_video: UploadFile = File(...), audio_file: UploadFile = File(None)):
    task_id = str(uuid.uuid4())[:8]
    ext = source_video.filename.split(".")[-1].lower() if source_video.filename else "mp4"
    source_path = f"/tmp/{task_id}_source.{ext}"
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    with open(source_path, "wb") as f: f.write(await source_video.read())
    # 转码视频为标准h264格式，避免HeyGem解码问题
    converted_path = f"/tmp/{task_id}_source_h264.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", source_path, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", converted_path], capture_output=True)
    if os.path.exists(converted_path) and os.path.getsize(converted_path) > 0:
        source_path = converted_path
    if audio_file and audio_file.filename:
        audio_path = f"/tmp/{task_id}_audio.mp3"
        with open(audio_path, "wb") as f: f.write(await audio_file.read())
    else:
        audio_path = f"/tmp/{task_id}_audio.wav"
        subprocess.run(["ffmpeg", "-y", "-i", source_path, "-ar", "16000", "-ac", "1", audio_path], capture_output=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_liveportrait, args=(task_id, source_path, audio_path, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})



# ===================================================
# CosyVoice 声音克隆 TTS
# ===================================================
def run_cosyvoice_tts(task_id, text, prompt_wav_path, prompt_text, speed, out_path):
    tasks[task_id] = {"status": "running", "step": "声音克隆生成中"}
    try:
        wav_file = f"{out_path}/audio.wav"
        audio_file = f"{out_path}/audio.mp3"
        # 清理文本：去掉换行、转简体
        import re as _re
        text = _re.sub(r'[\r\n]+', '，', text).strip()
        text = _re.sub(r'[，,]{2,}', '，', text)
        try:
            import opencc
            cc = opencc.OpenCC('t2s')
            text = cc.convert(text)
            prompt_text = cc.convert(prompt_text)
        except: pass
        import json as _json
        params_file = f"{out_path}/params.json"
        with open(params_file, 'w') as f:
            _json.dump({"text": text, "prompt_text": prompt_text, "prompt_wav": prompt_wav_path, "wav_file": wav_file, "speed": speed}, f, ensure_ascii=False)
        script = f"""
import sys, json, torch, ctypes
# 加载CUDA库
for lib in ['/root/miniconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cu13/lib/libcudart.so.13']:
    try: ctypes.CDLL(lib)
    except: pass
sys.path.insert(0, '/root/CosyVoice')
import os
os.chdir('/root/CosyVoice')
from cosyvoice.cli.cosyvoice import CosyVoice2
import torchaudio
with open(r'{params_file}') as f:
    p = json.load(f)
model = CosyVoice2('/root/autodl-tmp/CosyVoice/pretrained_models/CosyVoice2-0.5B', load_jit=False)
speech, sr = torchaudio.load(p['prompt_wav'])
if sr != 16000:
    speech = torchaudio.transforms.Resample(sr, 16000)(speech)
chunks = []
for i, j in enumerate(model.inference_zero_shot(p['text'], p['prompt_text'], speech, stream=False, speed=p['speed'])):
    chunks.append(j['tts_speech'])
if chunks:
    full_audio = torch.cat(chunks, dim=-1)
    torchaudio.save(p['wav_file'], full_audio, model.sample_rate)
"""
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = '/root/miniconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cu13/lib:/usr/local/cuda/lib64:' + env.get('LD_LIBRARY_PATH', '')
        script_path = f"{out_path}/cosyvoice_run.py"
        with open(script_path, 'w', encoding='utf-8') as _sf:
            _sf.write(script)
        result = subprocess.run(
            ['/root/run_cosyvoice.sh', script_path],
            capture_output=True, text=True, timeout=300, env=env
        )
        if result.returncode != 0:
            tasks[task_id] = {"status": "failed", "error": result.stderr[-500:]}
            return
        subprocess.run(["ffmpeg", "-y", "-i", wav_file, audio_file], capture_output=True)
        tasks[task_id] = {"status": "done", "type": "audio", "audio_url": f"{BACKEND_URL}/file/{task_id}/audio.mp3"}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}


@app.post("/clone-tts")
async def clone_tts(
    text: str = Form(...),
    prompt_text: str = Form(...),
    speed: float = Form(default=1.0),
    voice_sample: UploadFile = File(...)
):
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    # 保存声音样本
    ext = voice_sample.filename.split(".")[-1].lower()
    raw_path = f"{out_path}/prompt.{ext}"
    wav_path = f"{out_path}/prompt.wav"
    with open(raw_path, "wb") as f: f.write(await voice_sample.read())
    # 转换为wav
    subprocess.run(["ffmpeg", "-y", "-i", raw_path, "-ar", "16000", "-ac", "1", wav_path], capture_output=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_cosyvoice_tts, args=(task_id, text, wav_path, prompt_text, speed, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """用Whisper转录用户上传的声音样本"""
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    ext = audio.filename.split(".")[-1].lower()
    raw_path = f"{out_path}/input.{ext}"
    wav_path = f"{out_path}/input.wav"
    with open(raw_path, "wb") as f: f.write(await audio.read())
    subprocess.run(["ffmpeg", "-y", "-i", raw_path, "-ar", "16000", "-ac", "1", wav_path], capture_output=True)
    try:
        r = get_whisper_model().transcribe(wav_path, language="zh")
        text = r["text"]
        try:
            import opencc; text = opencc.OpenCC('t2s').convert(text)
        except: pass
        return JSONResponse({"success": True, "text": text})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})



# ===================================================
# CosyVoice 声音克隆 TTS
# ===================================================


def run_merge(task_id, video_path, audio_path, subtitle_text, bgm_file, font_file, out_path, user=""):
    tasks[task_id] = {"status": "running", "step": "合并视频音频字幕"}
    try:
        srt_path = f"{out_path}/subtitle.srt"
        # 用Whisper生成精准时间戳字幕
        try:
            result = get_whisper_model().transcribe(audio_path, language="zh", word_timestamps=True)
            with open(srt_path, "w", encoding="utf-8") as f:
                idx = 1
                for seg in result["segments"]:
                    start = seg["start"]
                    end = seg["end"]
                    text = seg["text"].strip()
                    if not text: continue
                    sh, sm, ss = int(start)//3600, (int(start)%3600)//60, start%60
                    eh, em, es = int(end)//3600, (int(end)%3600)//60, end%60
                    ss_fmt = f"{ss:06.3f}".replace(".", ",")
                    es_fmt = f"{es:06.3f}".replace(".", ",")
                    f.write(f"{idx}\n{sh:02d}:{sm:02d}:{ss_fmt} --> {eh:02d}:{em:02d}:{es_fmt}\n{text}\n\n")
                    idx += 1
        except Exception as e:
            # 失败则回退到按句子分割
            sentences = [s.strip() for s in re.split(r"[，。！？,!?\n]", subtitle_text) if s.strip()]
            duration_per = 3
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, w in enumerate(sentences):
                    start = i * duration_per
                    end = start + duration_per
                    sh, sm, ss = start//3600, (start%3600)//60, start%60
                    eh, em, es = end//3600, (end%3600)//60, end%60
                    f.write(f"{i+1}\n{sh:02d}:{sm:02d}:{ss:02d},000 --> {eh:02d}:{em:02d}:{es:02d},000\n{w}\n\n")

        font_name = os.path.splitext(font_file)[0] if font_file else "AlimamaShuHeiTi-Bold"
        subtitle_style = "FontName=Noto Sans CJK SC,FontSize=40,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Bold=1,Shadow=1,WrapStyle=0,MarginV=30,PlayResX=720,PlayResY=1280"
        output_file = f"{out_path}/final.mp4"
        bgm_path = f"/root/autodl-tmp/assets/bgm/{bgm_file}" if bgm_file else ""

        if bgm_path and os.path.exists(bgm_path):
            cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path, "-i", bgm_path,
                   "-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.12[bgm];[voice][bgm]amix=inputs=2:duration=first[aout]",
                   "-vf", f"subtitles={srt_path}:force_style=\'{subtitle_style}\'",
                   "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-c:a", "aac", "-shortest", output_file]
        else:
            cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                   "-vf", f"subtitles={srt_path}:force_style=\'{subtitle_style}\'",
                   "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-c:a", "aac", "-shortest", output_file]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            tasks[task_id] = {"status": "failed", "error": result.stderr[-500:]}
            return
        final_url = f"{BACKEND_URL}/file/{task_id}/final.mp4"
        tasks[task_id] = {"status": "done", "type": "final", "video_url": final_url}
        save_history({"task_id": task_id, "video_url": final_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M"), "subtitle": subtitle_text[:50]}, user)
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/merge")
async def merge(video_url: str = Form(...), audio_url: str = Form(...),
                subtitle_text: str = Form(...), bgm_type: str = Form(default=""),
                bgm_file: str = Form(default=""), font_file: str = Form(default=""),
                user: str = Form(default="")):
    import urllib.request as ur
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    video_path = f"{out_path}/input.mp4"
    audio_path = f"{out_path}/input.mp3"
    # 如果是本地URL直接复制文件，避免网络请求卡死
    def download(url, path):
        if url.startswith(BACKEND_URL):
            local = url.replace(BACKEND_URL, "").replace("/file/", f"{OUTPUT_DIR}/").replace("/", "/", 1)
            parts = url.replace(BACKEND_URL + "/file/", "").split("/")
            local_path = f"{OUTPUT_DIR}/{parts[0]}/{parts[1]}"
            if os.path.exists(local_path):
                import shutil
                shutil.copy(local_path, path)
                return
        req = ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with ur.urlopen(req, timeout=60) as r:
            with open(path, "wb") as f: f.write(r.read())
    download(video_url, video_path)
    download(audio_url, audio_path)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_merge, args=(task_id, video_path, audio_path, subtitle_text, bgm_file or bgm_type, font_file, out_path, user), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

# ===================================================
# 通用接口
# ===================================================
@app.get("/status/{task_id}")
def get_status(task_id: str):
    return JSONResponse(tasks.get(task_id, {"status": "not_found"}))

@app.get("/file/{task_id}/{filename}")
def get_file(task_id: str, filename: str):
    path = f"{OUTPUT_DIR}/{task_id}/{filename}"
    if not os.path.exists(path):
        return JSONResponse({"error": "文件不存在"}, status_code=404)
    return FileResponse(path)

@app.get("/voices")
def get_voices():
    return JSONResponse({"voices": [
        {"id": "xiaoxiao", "name": "晓晓", "desc": "温柔女声"},
        {"id": "xiaoyi",   "name": "晓伊", "desc": "活泼女声"},
        {"id": "yunjian",  "name": "云健", "desc": "成熟男声"},
        {"id": "yunxi",    "name": "云希", "desc": "阳光男声"},
        {"id": "yunxia",   "name": "云夏", "desc": "自然男声"},
        {"id": "yunyang",  "name": "云扬", "desc": "播音男声"},
    ]})


@app.post("/upload-bgm")
async def upload_bgm(file: UploadFile = File(...)):
    bgm_dir = "/root/autodl-tmp/assets/bgm"
    os.makedirs(bgm_dir, exist_ok=True)
    safe_name = re.sub(r'[^\w\u4e00-\u9fff.\-]', '_', file.filename or "bgm.mp3")
    dest = f"{bgm_dir}/{safe_name}"
    with open(dest, "wb") as f:
        f.write(await file.read())
    return JSONResponse({"filename": safe_name})

@app.get("/bgm/{filename}")
def get_bgm(filename: str):
    path = f"/root/autodl-tmp/assets/bgm/{filename}"
    if not os.path.exists(path):
        return JSONResponse({"error": "文件不存在"}, status_code=404)
    return FileResponse(path)

@app.get("/fonts")
def get_fonts():
    import glob
    fonts = [os.path.basename(f) for f in glob.glob("/root/autodl-tmp/assets/fonts/*")]
    return JSONResponse({"fonts": fonts})


HISTORY_FILE = "/root/autodl-tmp/history.json"

def save_history(record: dict, user: str = ""):
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        record["user"] = user
        history.insert(0, record)
        history = history[:100]  # 最多保存100条
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, ensure_ascii=False)
    except: pass

@app.get("/history")
def get_history(user: str = ""):
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                all_history = json.load(f)
                if user:
                    all_history = [h for h in all_history if h.get("user") == user]
                return JSONResponse({"success": True, "history": all_history})
    except: pass
    return JSONResponse({"success": True, "history": []})


INVITE_FILE = "/root/autodl-tmp/invites.json"

def load_invites():
    if os.path.exists(INVITE_FILE):
        with open(INVITE_FILE, 'r') as f:
            return json.load(f)
    return {"codes": []}

def save_invites(data):
    with open(INVITE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.post("/invite/verify")
async def verify_invite(request: Request):
    body = await request.json()
    code = body.get("code", "").strip().upper()
    data = load_invites()
    for item in data["codes"]:
        if item["code"] == code:
            if item["status"] == "active":
                return JSONResponse({"success": True, "message": "验证成功"})
            return JSONResponse({"success": False, "message": "邀请码已禁用"})
    return JSONResponse({"success": False, "message": "邀请码无效"})

@app.post("/invite/generate")
async def generate_invites(request: Request):
    body = await request.json()
    secret = body.get("secret", "")
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or secret != admin_secret:
        return JSONResponse({"success": False, "message": "无权限"}, status_code=403)
    count = body.get("count", 10)
    data = load_invites()
    new_codes = []
    for _ in range(count):
        code = "INV-" + uuid.uuid4().hex[:8].upper()
        data["codes"].append({"code": code, "status": "active", "created_at": datetime.now().isoformat()})
        new_codes.append(code)
    save_invites(data)
    return JSONResponse({"success": True, "codes": new_codes})

@app.get("/invite/list")
async def list_invites(secret: str = ""):
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or secret != admin_secret:
        return JSONResponse({"success": False, "message": "无权限"}, status_code=403)
    data = load_invites()
    return JSONResponse({"success": True, "codes": data["codes"]})


VOICE_PROFILE_DIR = "/root/autodl-tmp/voice_profiles"
os.makedirs(VOICE_PROFILE_DIR, exist_ok=True)

@app.post("/voice/save")
async def save_voice_profile(
    name: str = Form(...),
    prompt_text: str = Form(...),
    voice_sample: UploadFile = File(...)
):
    profile_dir = f"{VOICE_PROFILE_DIR}/{name}"
    os.makedirs(profile_dir, exist_ok=True)
    ext = voice_sample.filename.split(".")[-1].lower()
    raw_path = f"{profile_dir}/sample.{ext}"
    wav_path = f"{profile_dir}/sample.wav"
    with open(raw_path, "wb") as f: f.write(await voice_sample.read())
    subprocess.run(["ffmpeg", "-y", "-i", raw_path, "-ar", "16000", "-ac", "1", wav_path], capture_output=True)
    with open(f"{profile_dir}/meta.json", "w") as f:
        json.dump({"name": name, "prompt_text": prompt_text, "wav_path": wav_path}, f, ensure_ascii=False)
    return JSONResponse({"success": True, "message": f"声音档案已保存"})

@app.get("/voice/list")
def list_voice_profiles():
    profiles = []
    if os.path.exists(VOICE_PROFILE_DIR):
        for d in os.listdir(VOICE_PROFILE_DIR):
            meta_path = f"{VOICE_PROFILE_DIR}/{d}/meta.json"
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    profiles.append(json.load(f))
    return JSONResponse({"success": True, "profiles": profiles})

@app.delete("/voice/{name}")
def delete_voice_profile(name: str):
    profile_dir = f"{VOICE_PROFILE_DIR}/{name}"
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
        return JSONResponse({"success": True})
    return JSONResponse({"success": False, "message": "档案不存在"})

@app.post("/clone-tts-profile")
async def clone_tts_with_profile(
    text: str = Form(...),
    profile_name: str = Form(...),
    speed: float = Form(default=1.0)
):
    meta_path = f"{VOICE_PROFILE_DIR}/{profile_name}/meta.json"
    if not os.path.exists(meta_path):
        return JSONResponse({"success": False, "error": "声音档案不存在"}, status_code=404)
    with open(meta_path) as f:
        meta = json.load(f)
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_cosyvoice_tts, args=(task_id, text, meta["wav_path"], meta["prompt_text"], speed, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

@app.get("/health")
def health():
    return {"status": "ok", "services": ["liveportrait","tts","merge","rewrite","fetch-video","generate-title","user-videos","machine-code","verify-license"]}

# ===================================================
# 抖音扫码登录
# ===================================================
_qr_sessions = {}  # token -> {cookie, status}

@app.get("/douyin-qrcode")
async def get_douyin_qrcode():
    try:
        import urllib.request as ur
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.douyin.com/",
        }
        url = "https://sso.douyin.com/get_qrcode/?service=https%3A%2F%2Fwww.douyin.com&need_logo=false&need_short_url=true&device_platform=web_app&aid=6383&account_sdk_source=sso&sdk_version=2.2.5-rc.6&language=zh"
        req = ur.Request(url, headers=headers)
        with ur.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        token = data["data"]["token"]
        qrcode_url = data["data"]["qrcode_index_url"]
        _qr_sessions[token] = {"status": "waiting", "cookie": ""}
        return JSONResponse({"token": token, "qrcode_url": qrcode_url})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/douyin-qrcode/poll/{token}")
async def poll_douyin_qrcode(token: str):
    try:
        import urllib.request as ur
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.douyin.com/",
        }
        url = f"https://sso.douyin.com/check_qrconnect/?token={token}&service=https%3A%2F%2Fwww.douyin.com&need_logo=false&device_platform=web_app&aid=6383&account_sdk_source=sso&sdk_version=2.2.5-rc.6"
        req = ur.Request(url, headers=headers)
        with ur.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        status = data.get("data", {}).get("status", 0)
        # status: 1=待扫码, 2=已扫码, 3=已确认, 4=已过期
        if status == 3:
            redirect_url = data["data"].get("redirect_url", "")
            if redirect_url:
                # 用 Playwright 跟随跳转，捕获最终 cookie
                def capture():
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        ctx = browser.new_context(ignore_https_errors=True)
                        page = ctx.new_page()
                        page.goto(redirect_url, wait_until="networkidle", timeout=30000)
                        cookies = ctx.cookies("https://www.douyin.com")
                        browser.close()
                        return "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("value"))
                cookie_str = capture()
                _qr_sessions[token] = {"status": "done", "cookie": cookie_str}
                return JSONResponse({"status": "done", "cookie": cookie_str})
        elif status == 4:
            return JSONResponse({"status": "expired"})
        elif status == 2:
            return JSONResponse({"status": "scanned"})
        else:
            return JSONResponse({"status": "waiting"})
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6006)
