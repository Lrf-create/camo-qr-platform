# GitHub 操作步骤

仓库：<https://github.com/Lrf-create/camo-qr-platform>（私有，需要登录有权限的账号）。

## 查看与下载

1. 登录 GitHub，打开上方仓库。
2. 首页查看 README，打开 `docs` 阅读运行说明。
3. 点击绿色 `Code` → `Download ZIP` 下载源码，或使用 Git 克隆。
4. 当前电脑继续用原桌面“Camo扫码平台”；下载源码不影响现有运行环境。

## 后续更新源码

独立整理目录为 `D:\医院\CODEX开发\github-release\camo-qr-platform`。运行中的程序在原目录，修改不会自动同步到整理目录；上传前应将需要发布的源码变更复制到整理目录，排除私密配置和运行文件。

在整理目录打开终端：

```powershell
git status
git diff
git add .
git diff --cached --stat
git commit -m "说明本次功能修改"
git push
```

首次 Git 认证按官方页面提示自行登录，不要把密码或令牌写进命令、源码或文档。推送前检查暂存内容，避免包含真实数据库、账号、密钥或日志。

## 使用 GitHub 网页上传（Git 无法认证时）

打开仓库 → `Add file` → `Upload files`，上传整理目录内的源码文件和子目录，保留目录结构，然后填写提交说明并提交。不要上传外层 `github-release` 目录、`.git` 或完整运行环境；浏览器上传数量限制时分批提交。

## 其他电脑获取

```powershell
git clone https://github.com/Lrf-create/camo-qr-platform.git
```

获取源码后按 [本机运行说明](本机运行说明.md) 准备运行环境。真实业务数据库需要另行安全备份，GitHub 源码仓库不承担数据库备份。
