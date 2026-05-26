# StackChan 工程手册

这份文档沉淀本仓库的工程结构、常用命令和本地调试步骤。给人和自动化 Agent 都优先读这里。

## 仓库结构

- `firmware/`: ESP-IDF 固件工程，当前主要工作区。
- `app/`: 移动端 App。
- `remote/`: 遥控器相关代码。
- `server/`: 服务端相关代码。

固件里常用路径：

- `firmware/main/`: 主应用组件，`CMakeLists.txt` 会递归收集 `apps/`、`assets/`、`hal/`、`stackchan/` 下的 C/C++ 源码。
- `firmware/main/hal/board/stackchan_display.cc`: StackChan 主显示/Avatar 接入点，当前主界面 Avatar 在这里实例化。
- `firmware/main/stackchan/avatar/`: Avatar 框架、皮肤、装饰器。
- `firmware/main/stackchan/avatar/skins/default/`: 默认几何图形皮肤。
- `firmware/main/stackchan/avatar/skins/akusa/`: 明日香皮肤，使用 6 张 `320x240` RGB565 全屏表情帧。
- `firmware/main/stackchan/modifiers/`: 表情、眨眼、说话、呼吸、待机动作等 modifier。
- `firmware/main/Kconfig.projbuild`: 工程 Kconfig，包括唤醒词相关配置。
- `firmware/partitions.csv`: 分区表，当前 `assets` 分区为 `5M`。

## 本地环境

本机已知可用环境：

- 仓库路径：`Y:\StackChan`
- 固件路径：`Y:\StackChan\firmware`
- ESP-IDF：`Y:\esp-idf-v5.5.4`
- 稳定烧录端口：`COM4`
- 稳定烧录波特率：`115200`
- 目标芯片：ESP32-S3

PowerShell 下执行 ESP-IDF 命令时使用：

```powershell
cmd /c "Y:\esp-idf-v5.5.4\export.bat && idf.py build"
```

如果移动、删除、重命名了源码目录，先重配置：

```powershell
cmd /c "Y:\esp-idf-v5.5.4\export.bat && idf.py reconfigure build"
```

烧录：

```powershell
cmd /c "Y:\esp-idf-v5.5.4\export.bat && idf.py -p COM4 -b 115200 flash"
```

查看串口：

```powershell
Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name,Description
```

如果 `COM4` 不出现，拔插 USB；必要时按住 `BOOT`，点一下 `RESET`，再松开 `BOOT` 进入下载模式。

## 构建与资源

常规流程：

1. 进入 `firmware/`。
2. 首次或依赖缺失时运行 `python ./fetch_repos.py`。
3. 执行 `idf.py build`。
4. 执行 `idf.py -p COM4 -b 115200 flash`。

当前固件会构建并烧录 `generated_assets.bin` 到 `assets` 分区。自定义唤醒词启用 MultiNet 后，`generated_assets.bin` 约 4.7MB，所以 `assets` 分区已经从 4M 调整为 5M：

```csv
assets, data, spiffs, 0xA00000, 5M,
```

不要随手把它改回 4M，否则设备可能启动后找不到 `index.json` 或语音模型资源。

## Avatar 与表情

核心类型：

- `avatar::Avatar`: Avatar 基类，维护 `_key_elements` 和 `_emotion`。
- `Emotion`: 定义在 `firmware/main/stackchan/avatar/avatar/elements/emotion.h`，枚举包括 `Neutral`、`Happy`、`Angry`、`Sad`、`Doubt`、`Sleepy`。
- `Feature`: 眼睛、嘴等关键元素接口，`setWeight()` 被说话动画用来驱动嘴巴开合。
- `SpeakingModifier`: 周期性调用 `avatar.mouth().setWeight(...)`。
- `IdleExpressionModifier`: 待机时轻微移动眼睛/嘴巴。

默认皮肤用 LVGL 几何对象画眼睛和嘴。`akusa` 皮肤用整张图片帧切换：

- `firmware/main/stackchan/avatar/skins/akusa/akusa.h`
- `firmware/main/stackchan/avatar/skins/akusa/akusa.cpp`
- `firmware/main/stackchan/avatar/skins/akusa/assets/akusa_face.c`

`akusa` 资源符号：

- `akusa_face_neutral`
- `akusa_face_happy`
- `akusa_face_angry`
- `akusa_face_sad`
- `akusa_face_doubt`
- `akusa_face_sleepy`

当前主显示入口在 `stackchan_display.cc` 中创建：

```cpp
auto avatar = std::make_unique<AkusaAvatar>();
```

新增图片皮肤的推荐方式：

1. 在 `firmware/main/stackchan/avatar/skins/<skin_name>/` 新建 `.h/.cpp/assets/`。
2. 在 `firmware/main/stackchan/avatar/avatar.h` include 新皮肤头文件。
3. 将 PNG 转为 LVGL RGB565 C 资源，符号名保持稳定。
4. 在皮肤的 `updateFrame()` 或对应逻辑里按 `Emotion` 选择 `lv_image_dsc_t`。
5. 在 `stackchan_display.cc` 或对应 app 入口实例化新 Avatar。
6. 执行 `idf.py reconfigure build`，因为源码目录变动可能需要重新扫描 glob。

图片资源注意：

- 目标屏幕是 `320x240`。
- 全屏 RGB565 一帧是 `320 * 240 * 2 = 153600` 字节。
- 6 张全屏表情约 900KB，当前 app 分区仍可容纳，但空间只有约 9% 余量。
- 如果继续加 12 张或更多帧，优先评估 app 分区大小、压缩情况和是否能把资源改走 assets 分区。

## 唤醒词

当前配置使用自定义中文唤醒词“咕咕嘎嘎”：

```ini
CONFIG_USE_CUSTOM_WAKE_WORD=y
CONFIG_CUSTOM_WAKE_WORD="gu gu ga ga"
CONFIG_CUSTOM_WAKE_WORD_DISPLAY="咕咕嘎嘎"
CONFIG_CUSTOM_WAKE_WORD_THRESHOLD=20
CONFIG_SR_MN_CN_MULTINET7_QUANT=y
```

这些配置同时写在：

- `firmware/sdkconfig`
- `firmware/sdkconfig.defaults`

`CONFIG_CUSTOM_WAKE_WORD` 使用拼音，词之间用空格分隔。阈值越小越敏感，当前为 20。

如果改唤醒词：

1. 修改 `sdkconfig.defaults`，必要时同步 `sdkconfig`。
2. 确认启用 `CONFIG_USE_CUSTOM_WAKE_WORD`。
3. 确认中文 MultiNet 模型开启，例如 `CONFIG_SR_MN_CN_MULTINET7_QUANT=y`。
4. 执行 `idf.py reconfigure build`，让 `generated_assets.bin` 重新生成。
5. 烧录时确保 assets 分区也被写入。

## 常见问题

- **改了目录名后 build 还找旧路径**：运行 `idf.py reconfigure build`。
- **烧录失败或找不到 COM4**：检查串口列表，拔插 USB，必要时手动进下载模式。
- **启动后资源找不到**：检查 `generated_assets.bin` 是否烧录，检查 `assets` 分区是否足够大。
- **图片皮肤没有随说话变化**：确认 `mouth().setWeight()` 是否被皮肤转化为帧切换或嘴部动画。
- **工作区已有未提交变更**：不要随意 reset 或 checkout，先确认变更来源和任务范围。

## 当前约定

- 文档和代码改动尽量保持小范围。
- 手工编辑文件优先使用 patch。
- 生成的图片资源可以用脚本批量转换为 C 数组。
- 烧录前至少跑一次 `idf.py build`。
- 涉及目录新增/删除/重命名时跑 `idf.py reconfigure build`。
