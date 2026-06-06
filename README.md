# AutoCheckIn

赛尔号 17 周年活动页自动签到脚本。

## 使用

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

编辑 `.env` 填入账号密码，然后运行：

```powershell
docker compose run --rm autocheckin
```

脚本会把登录状态保存在 `./data/session.json`，截图等诊断文件保存在 `./data/artifacts`。

## GitHub 和 Docker

本仓库带有 GitHub Actions workflow，会在 push 到 `main` 或手动运行时构建 Docker 镜像，并发布到 GitHub Container Registry：

```text
ghcr.io/Murmansk5000/seer17:latest
```

如果要发布到 Docker Hub，在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 添加两个 Repository secrets：

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

之后每次 push 到 `main` 会额外发布：

```text
docker.io/<DOCKERHUB_USERNAME>/seer17:latest
```

从远端镜像运行：

```powershell
docker run --rm `
  -e MIMI_ID=767448103 `
  -e MIMI_PASSWORD=your-password `
  -v ${PWD}/data:/data `
  ghcr.io/Murmansk5000/seer17:latest
```

## 第一次登录

第一次登录建议使用 GUI 模式。脚本会打开登录页、先尝试切到“米米号登录”，你只需要在浏览器里完成账号登录和滑块验证；登录成功后会话会保存在 `./data/session.json`，之后 Docker 普通运行会自动复用，不需要手动找 cookies。

本机运行：

```powershell
pip install -r requirements.txt
python -m playwright install chromium
$env:FIRST_LOGIN_GUI="true"
$env:HEADLESS="false"
$env:DATA_DIR="$PWD\data"
python autocheckin.py
```

如果要用 Docker 做 GUI，需要宿主机提供图形显示环境；Windows Docker Desktop 默认容器窗口不会直接显示。更省事的做法是在本机先用上面的 GUI 模式完成一次登录生成 `./data/session.json`，再让 Docker 复用这个文件。

## Unraid

推荐用一体化 GUI 模式在 Unraid 容器里完成首次登录。这样 `session.json` 直接在 Unraid/Chromium 环境生成，不需要从 PC 搬文件。

Unraid 模板里添加路径：

```text
Container Path: /data
Host Path: /mnt/user/appdata/seer17
```

添加端口：

```text
Container Port: 6080
Host Port: 6080
Protocol: TCP
```

首次登录时添加变量：

```text
GUI=true
```

启动容器后打开：

```text
http://UnraidIP:6080/vnc.html
```

在网页里的 Chromium 完成米米号登录/滑块。成功后容器会保存：

```text
/mnt/user/appdata/seer17/session.json
```

之后把 `GUI` 改成 `false` 或删除这个变量，保留 `/data` 挂载，容器就会 headless 自动签到。

如果 `/mnt/user/appdata/seer17/session.json` 不存在，普通 headless 模式会自动创建一个空文件并退出，提示你先填入或用 GUI 模式生成。

手动查看文件：

```bash
ls -lah /mnt/user/appdata/seer17
cat /mnt/user/appdata/seer17/session.json | head
```

## 验证码

当前登录页可能出现“拖动下方拼图完成验证”。脚本不会绕过验证码；遇到验证码会截图并退出。通过一次登录后，后续可复用 `./data/session.json` 或 `SESSION_JSON_BASE64` 中的会话继续签到。

## 环境变量

- `MIMI_ID`: 米米号
- `MIMI_PASSWORD`: 密码
- `GUI`: Unraid/noVNC GUI 模式，设为 `true` 时打开 `6080` 网页浏览器
- `VNC_RESOLUTION`: GUI 分辨率，默认 `1280x900x24`
- `HEADLESS`: 是否无头运行，默认 `true`
- `BROWSER_EXECUTABLE`: 浏览器路径，Docker 镜像内默认 `/usr/bin/chromium`
- `SESSION_FILE`: 登录状态文件路径，默认 `/data/session.json`
- `SESSION_JSON_BASE64`: 可选，base64 编码后的登录状态 JSON
- `SESSION_JSON`: 可选，原始登录状态 JSON
- `FIRST_LOGIN_GUI`: 首次登录 GUI 模式，默认 `false`
- `LOGIN_WAIT_SECONDS`: GUI 模式等待登录完成的秒数，默认 `300`
- `ALLOW_PASSWORD_LOGIN`: 是否尝试账号密码登录，默认 `true`
