# GeoPin 

[中文](./README.md) | [English](./README_EN.md)

![Typer CLI](https://img.shields.io/badge/CLI-Typer-2E8B57?logo=python&logoColor=white)
![Pixi Env](https://img.shields.io/badge/Env-Pixi-7B61FF)
![Compile Passing](https://img.shields.io/badge/Compile-Passing-brightgreen)

将 DJI 视频中的遥测数据与 KML 地标结合，生成动态字幕叠加（ASS）并烧录输出新视频。  

## 1. 功能

1. 解析 KML 中的 `Placemark` 地标（经纬高、名称、样式颜色、可选时间戳）。
2. 从 DJI 视频字幕流 `0:s:0` 中提取遥测信息（时间、经纬高、云台姿态、焦距）。
3. 探测视频分辨率、帧率、时长与总帧数。
4. 将稀疏遥测插值为逐帧轨迹，导出 `flight_trajectory.csv`。
5. 计算地标在每帧中的可见性与投影像素位置，生成 `overlay_dynamic.ass`。
6. 输出运行报告 `overlay_report.json`。
7. 通过 ffmpeg 将 ASS 烧录到视频，得到叠加后 MP4。

## 2. 环境配置

### 2.1 运行环境要求

- 安装 `pixi`

### 2.2 初始化环境

```powershell
cd <项目根路径>
pixi install
pixi shell
```
## 3. 使用方法

### 3.1 快速开始

```powershell
pixi run geopin
  --kml input/my_points.kml 
  --video input/my_dji_video.MP4 
  --output output/my_run
```
### 3.2 参数说明

可通过下面命令查看帮助信息：
```powershell
pixi run geopin --help
```

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--kml` | KML 地标文件路径 | `input/xxx.kml` |
| `--video` | DJI 原始视频路径（需含可解析字幕流） | `input/xxx.MP4` |
| `--output` | 输出目录路径 | `output/xxx` |
| `--font-name` | ASS 字体名 | `Microsoft YaHei` |
| `--font-size` | ASS 字号 | `60` |
| `--max-ground-distance` | 地面水平距离上限（米）；负值关闭 | `1000.0` |
| `--dry-run` | 跳过最终 ffmpeg 烧录步骤 | 关闭 |

## 4. 输入输出

### 4.1 输入

1. 视频文件（`--video`）
- 格式：MP4（或 ffmpeg 可读取格式）
- 必要条件：包含字幕流 `0:s:0`
- 字幕中需可匹配字段：`FrameCnt`、`latitude/longitude`、`rel_alt/abs_alt`、`gb_yaw/gb_pitch/gb_roll`、`focal_len`

2. Google earth KML 文件（`--kml`）
- 使用 `Placemark` + `coordinates`（经度,纬度,高程）
- 可选 `name`（为空时自动命名 `P{index}`）
- 可选 `styleUrl/Style/StyleMap`（用于颜色）
- 可选在 `description` 中包含时间串：`YYYY-MM-DD HH:MM:SS`

3. 输出目录（`--output`）
- 程序会自动创建目录

### 4.2 输出

执行后会在 `--output` 目录生成：

1. `<video_stem>_overlay.mp4`
- 叠加地标文字后的最终视频
- 仅在非 `--dry-run` 时生成

2. `overlay_dynamic.ass`
- 动态字幕脚本（逐帧可见点事件）

3. `flight_trajectory.csv`
- 逐帧轨迹数据
- 列定义：
  - `frame_index,time_s,timestamp,latitude,longitude,abs_alt,yaw,pitch,roll,focal_len`

4. `overlay_report.json`
- 运行统计与结果摘要
- 主要字段：
  - 输入输出路径：`video,kml,output,ass,trajectory_csv`
  - 视频信息：`frame_count,fps,video_duration_s`
  - 遥测时间范围：`telemetry_start,telemetry_end`
  - 可见性统计：`points_total,ass_events,visible_points`
  - 每个点统计：`point_stats[]`（含 `visible_frames/first_visible/last_visible`）

## 5. 项目引用格式

文本引用：

```text
wangjunfan. GeoPin: DJI 视频与 KML 地标动态叠加工具 (Version 0.1.0) [Computer software]. 2026.
```

BibTeX：

```bibtex
@software{geopin_2026,
  author  = {wangjunfan},
  title   = {GeoPin: DJI 视频与 KML 地标动态叠加工具},
  version = {0.1.0},
  year    = {2026},
  url     = {https://github.com/RefineM/GeoPin}
}
```
