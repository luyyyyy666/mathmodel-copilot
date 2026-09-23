# 科学图表

先确定每张图回答的问题，再按数据结构选择图型。参考 ../assets/figures/presets.md 的图型卡片、style.md 的字体/颜色/尺寸；matplotlib_templates.py 提供 20 类可调用模板。模板来自 Mathodology，MIT 许可和固定版本见同目录 LICENSE、provenance.json。卡片中的上游扩展资源不随本包提供；实际可执行模板以本地 Python 文件为准。

安装 assets/figures/requirements.txt 中的依赖到隔离环境。统计图必须从真实数据/计算结果生成；示意图注明用途，不能代替结果证据。没有空间坐标时不能发明地图。复杂图仅在问题需要时使用。记录种子、单位、误差条含义、字体和库版本。每张图保存 PNG 供检查，同时保存 PDF 或 SVG 矢量版。

通过 workflow.py run --stage figures 登记绘图脚本、数据为 --input，图像和计算结果为 --output。保存 figure-manifest.json，例如：

```json
{"figures":[{"id":"comparison","question":"模型是否优于基线？","caption":"同一数据上的目标函数比较，越低越好。","script":"figures.py","data":["results/comparison.json"],"outputs":["figures/comparison.png","figures/comparison.pdf"]}]}
```

每个数据文件必须来自登记的输入或本次执行输出。不得为了视觉美化修改计算数值。检查实际 PNG 的文字、单位、图例、配色、裁切和与数据一致性，再单独写 figure-review.json（不要修改已经登记输出的 manifest）：

```json
{"figures":[{"id":"comparison","status":"pass","sha256":"实际 PNG 的 SHA256","observations":"写下实际观察，包括数值对应、标签和裁切情况"}]}
```

没有图的题目用 {"figures":[],"reason":"具体说明为什么无需图表"}，不伪造图。图表更改后必须重新检查，旧哈希的审查无法通过。complete figures 时登记执行 ID；第三方代码的许可也要登记。检查记录由实际看过图的宿主 Agent 或人写入，脚本不会自动判定视觉质量。
