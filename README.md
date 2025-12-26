# State Popup (Home Assistant Custom Integration via HACS)

v1.1

当设备状态变化时，在前端弹出可定制的图片/GIF 背景通知卡片。

## 功能
- 监听所有或指定实体的状态变更，通过自定义 WebSocket 推送到前端。
- 前端弹窗支持背景图/GIF、文本颜色/位置/字号配置，淡入淡出动画。
- 冷却时间避免刷屏，支持实体/域名白名单与黑名单。

## 目录结构
```
custom_components/state_popup/
  ├─ __init__.py
  ├─ const.py
  └─ manifest.json
www/community/state_popup/
  └─ state_popup.js
hacs.json
README.md
```

## 安装（HACS 自定义仓库）
1. 将本仓库上传至 GitHub（保持上述结构）。
2. 在 Home Assistant → HACS → Integrations → 右上角三点 → Custom repositories：
   - Repository: 你的 GitHub 仓库地址
   - Category: Integration
3. 在 HACS 中搜索并安装 **State Popup**。
4. 前端资源会被放到 `/hacsfiles/state_popup/state_popup.js`，需在前端资源里手动添加：
   - 设置 → 仪表板 → 资源 → 添加资源  
   - URL: `/hacsfiles/state_popup/state_popup.js`  
   - 资源类型: JavaScript 模块
5. 重载前端缓存或刷新浏览器。

## 配置方式
### UI 配置（推荐）
1. 设置 → 设备与服务 → 添加集成 → 搜索 “State Popup” → 填写选项（实体/域名过滤、冷却、背景图、文字样式）。
2. 后续可在集成卡片里进入“配置”修改选项。

### YAML 配置（备用，不再推荐）
仍可在 `configuration.yaml` 中配置：

## 使用说明
- 任意被监听的实体状态变化时，前端会弹出卡片：`友好名: 旧值 → 新值 @ 时间`。
- 背景支持 GIF；文本带阴影以提升可读性；居中/顶部/底部对齐可配置。
- 5 秒后自动淡出，可按需调整（修改 `state_popup.js` 的 `setTimeout` 时长）。

## 注意
- `background_url` 需为可访问的 URL（http/https）。
- 若需更复杂的配置 UI，可后续添加 `config_flow.py`。
- 该集成无需额外权限，沿用 HA WebSocket 认证。
