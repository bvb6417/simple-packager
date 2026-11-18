"""Offline emoji search: Chinese aliases, Unicode English names, category or emoji."""
import unicodedata
from packager_core import EMOJI_LIBRARY

ALIASES = '''
🏠 主页 房屋 首页 home
⚙️ 设置 齿轮 配置
🔍 搜索 放大镜 查找 search
🧭 指南针 导航
📌 图钉 固定
🔙 返回 后退
🔝 顶部 置顶
🔄 刷新 重载 循环
➕ 添加 加号
➖ 减号 删除
❌ 叉 关闭 错误 取消
✅ 对勾 成功 完成 确认
ℹ️ 信息 帮助
🌐 地球 网络 网站
🍔 汉堡 菜单
🚪 门 退出
🔑 钥匙 密钥
🔒 锁 安全 加密
🔓 解锁
🛑 停止 禁止
⚠️ 警告 注意
🚫 禁止
❓ 问号 问题 帮助
❗ 感叹号 提醒
⬆️ 向上 上箭头
⬇️ 向下 下箭头 下载
⬅️ 向左 左箭头
➡️ 向右 右箭头
📦 包裹 打包 盒子 箱子 package box
📁 文件夹 目录 folder
📂 打开文件夹 目录
📄 文件 文档 纸张
📑 标签 书签 文档
📝 笔记 记录 编辑
✏️ 铅笔 写作 编辑
✒️ 钢笔 书写
💾 保存 软盘 save
📋 剪贴板 复制
✂️ 剪刀 剪切
📎 回形针 附件
🖇️ 回形针 附件
🗑️ 垃圾桶 删除 回收
📥 收件 下载 导入
📤 发件 上传 导出
🖨️ 打印 打印机
🖍️ 蜡笔 绘画
🖌️ 画笔 绘画
📏 尺子 测量
📐 三角尺 测量
🗂️ 文件夹 分类 卡片
🗃️ 文件箱 归档
🗄️ 文件柜 归档
🧾 收据 发票 账单
📖 打开的书 阅读 学习
📕 红书 书籍 学习
📗 绿书 书籍 学习
📘 蓝书 书籍 学习
📙 橙书 书籍 学习
📚 书籍 图书 学习
🎵 音符 音乐
🎶 音符 音乐
🎧 耳机 音乐
🎤 麦克风 唱歌 录音
🎥 摄像机 视频 电影
🎬 场记板 电影 视频
📺 电视 视频
📷 相机 拍照
📸 拍照 闪光灯 相机
🖼️ 图片 相框 图像
💬 聊天 消息 评论
🗨️ 对话 消息
💭 思考 想法
✉️ 邮件 信封
📧 邮箱 邮件
📨 邮件 收信
📞 电话 听筒
☎️ 电话 座机
🔔 铃铛 通知 提醒
🔕 静音 通知
📣 喇叭 公告
📢 扩音器 公告
▶️ 播放 视频
⏸️ 暂停 视频
⏹️ 停止 视频
👤 用户 个人
👥 用户 团队
🧑 人 成年人
👨 男人 男性
👩 女人 女性
🤝 握手 合作
👍 点赞 赞 好
👎 踩 差 反对
👏 鼓掌
🙌 庆祝 举手
🌟 星星 发光
⭐ 星星 收藏
❤️ 爱心 喜欢 红心
🏆 奖杯 冠军
🎖️ 奖章 荣誉
👑 皇冠
🛡️ 盾牌 安全 保护
👁️ 眼睛 查看
👣 脚印 足迹
🎁 礼物 赠品
🎉 庆祝 礼花 派对
🎈 气球
🎂 蛋糕 生日
🎓 毕业 学位 学生 学习
💼 公文包 工作
💍 戒指
💎 钻石
🛠️ 工具 修理 开发
🔧 扳手 工具 修理
🔨 锤子 工具
⛏️ 镐 工具
🔩 螺丝 工具
🧲 磁铁 吸引
🧪 试管 实验 科研
🧫 培养皿 实验 科研
🧬 基因 DNA 科研
🔬 显微镜 科研
🔭 望远镜 天文
📡 卫星 天线 信号
💻 电脑 笔记本 编程 开发 coding
🖥️ 电脑 显示器 桌面
⌨️ 键盘 输入
🖱️ 鼠标
🖲️ 轨迹球
🔋 电池 电量
🔌 插头 电源
💡 灯泡 灵感 想法
🔦 手电筒
📊 图表 柱状图 统计 数据
📈 上涨 趋势 图表 数据
📉 下跌 趋势 图表 数据
📅 日历 日期
📆 日历 日程
🕰️ 时钟 时间
⏰ 闹钟 提醒 时间
⏱️ 秒表 计时
🚀 火箭 启动 发射 rocket
😀 开心 笑脸 微笑
😁 咧嘴 开心 笑脸
😂 笑哭 开心
🤣 大笑 笑哭
😅 汗 笑脸 尴尬
😊 微笑 开心
😇 天使 微笑
🙂 微笑 笑脸
🙃 倒脸 微笑
😉 眨眼 笑脸
😍 喜欢 爱心 眼睛
🥰 喜欢 爱心 幸福
😘 亲吻 飞吻
😋 美味 好吃
😛 吐舌
🤪 疯狂 滑稽
🤔 思考 想 问题
🧐 观察 研究 单片眼镜
🤓 学霸 眼镜
😎 墨镜 酷
🤩 星星眼 崇拜
🥳 派对 庆祝
😒 无语 不开心
😞 失望 难过
😔 失落 难过
😢 哭泣 难过
😭 大哭 难过
😠 生气 愤怒
😡 愤怒 生气
🤬 生气 咒骂
🤯 爆炸 惊讶 震惊
😳 害羞 脸红
🥵 热 炎热
🥶 冷 寒冷
😱 惊恐 害怕
😨 害怕
🤗 拥抱
🤫 安静 嘘
🤥 撒谎
😶 无语 沉默
😐 无语 面无表情
🙄 白眼 无语
😴 睡觉 困
🤤 流口水
😵 头晕
🤢 恶心
🤮 呕吐
🤧 喷嚏 生病
😷 口罩 生病
🤡 小丑
👋 挥手 再见
👌 好的 手势
✌️ 胜利 耶
🤞 祝好运
🤟 爱你 手势
🤙 电话 手势
👉 右 指向
👈 左 指向
👆 上 指向
👇 下 指向
✊ 拳头 加油
👊 拳头
🙏 合十 感谢 祈祷
✍️ 写字 书写
💪 肌肉 力量 加油
🦵 腿
🦶 脚
👂 耳朵 听
👃 鼻子
🧠 大脑 思考
🫀 心脏
🫁 肺
🦷 牙齿
👀 眼睛 看
👄 嘴唇
💋 亲吻
🐶 狗 小狗
🐱 猫 小猫
🐭 老鼠
🐹 仓鼠
🐰 兔子
🦊 狐狸
🐻 熊
🐼 熊猫
🐨 考拉
🐯 老虎
🦁 狮子
🐮 牛
🐷 猪
🐸 青蛙
🐵 猴子
🐔 鸡
🐧 企鹅
🐦 鸟
🐤 小鸡
🦆 鸭子
🦅 鹰
🦉 猫头鹰
🦇 蝙蝠
🐺 狼
🐴 马
🦄 独角兽
🐝 蜜蜂
🐛 毛毛虫
🦋 蝴蝶
🐌 蜗牛
🐞 瓢虫
🐜 蚂蚁
🦟 蚊子
🕷 蜘蛛
🌸 樱花 花朵
🌹 玫瑰 花朵
🌺 花朵 木槿
🌻 向日葵 花朵
🌼 花朵 菊花
🌷 郁金香 花朵
🌱 幼苗 植物
🌲 树 松树
🌳 树 植物
🌴 椰树 热带
🌵 仙人掌
🌾 稻谷 麦穗
🌿 叶子 草 药草
🍀 幸运 四叶草
🍁 枫叶 秋天
🍂 落叶 秋天
🍃 叶子 风
🔥 火 火焰 热门
☀️ 太阳 晴天
⛅ 多云 天气
☁️ 云 天气
🌧 下雨 天气
⛈ 雷雨 天气
🌩 闪电 雷
🌨 下雪 天气
❄️ 雪花 冬天
☃️ 雪人
⛄ 雪人
💨 风
🌪 龙卷风
🌫 雾
🌈 彩虹
☔ 雨伞 下雨
🍎 苹果 水果
🍏 青苹果 水果
🍐 梨 水果
🍊 橘子 水果
🍋 柠檬 水果
🍌 香蕉 水果
🍉 西瓜 水果
🍇 葡萄 水果
🍓 草莓 水果
🫐 蓝莓 水果
🍑 桃子 水果
🥭 芒果 水果
🍍 菠萝 水果
🥝 猕猴桃 水果
🍅 西红柿 番茄
🥑 牛油果
🥦 西兰花 蔬菜
🥕 胡萝卜 蔬菜
🌽 玉米
🍞 面包
🥐 牛角包
🧀 奶酪
🍗 鸡腿
🥩 肉 牛排
🍟 薯条
🍕 披萨
🌭 热狗
🥪 三明治
☕ 咖啡 热饮
🫖 茶壶
🍵 茶
🥤 饮料
🧋 奶茶 珍珠
🧃 果汁
🥛 牛奶
🍺 啤酒
🍻 干杯 啤酒
🧡 橙心 爱心
💛 黄心 爱心
💚 绿心 爱心
💙 蓝心 爱心
💜 紫心 爱心
🖤 黑心 爱心
🤍 白心 爱心
🤎 棕心 爱心
💔 心碎 伤心
💯 满分 一百分
⚽ 足球 运动
🏀 篮球 运动
🏈 橄榄球 运动
⚾ 棒球 运动
🎾 网球 运动
🏐 排球 运动
🏓 乒乓球 运动
🎱 台球 运动
🎮 游戏 手柄
🕹️ 游戏 摇杆
🎲 骰子 随机
🧩 拼图 插件
🧸 玩具 熊
🔮 水晶球
🪄 魔法 魔杖
📱 手机 移动
⌚ 手表 时间
🕯️ 蜡烛
✨ 闪光 星星
'''


def normalize(text):
    return unicodedata.normalize('NFKC', text).casefold().replace('\ufe0f', '')


def make_catalog():
    aliases = {}
    for line in ALIASES.strip().splitlines():
        emoji, keywords = line.split(' ', 1)
        aliases[normalize(emoji)] = keywords
    records = []
    seen = {}
    for category, emojis in EMOJI_LIBRARY.items():
        for emoji in emojis:
            key = normalize(emoji)
            if key in seen:
                seen[key]['categories'].append(category)
                seen[key]['search'] += ' ' + normalize(category)
                continue
            english = ' '.join(unicodedata.name(char, '') for char in emoji)
            words = aliases.get(key, '')
            label = words.split()[0] if words else english.lower()
            record = dict(emoji=emoji, category=category, categories=[category], label=label,
                          search=normalize(f'{emoji} {category} {english} {words}'))
            seen[key] = record
            records.append(record)
    return records


CATALOG = make_catalog()


def search_emojis(query='', category='全部'):
    tokens = normalize(query).split()
    return [row for row in CATALOG if (category == '全部' or category in row['categories'])
            and all(token in row['search'] for token in tokens)]
