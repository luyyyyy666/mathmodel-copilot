# LaTeX 编译与页面检查

赛事论文先按 [格式配置](contest.md) 生成自己的主文件与章节安排；此处只处理编译和页面证据。编译成功不代表满足比赛页数、匿名或内容要求。

先运行 `python3 publication.py doctor`（脚本在 Skill scripts 目录），检查绘图、LaTeX 和 Poppler 环境。中文默认使用 assets/latex/main-zh.tex 的 ctex/项目内 TrueType 字体模板与 XeLaTeX 或 Tectonic；英文模板 main-en.tex 可使用 pdfLaTeX。模板是独立实现，吸收 math-model 的分章节论文、编译修复和页面检查流程；不假定特定比赛页数与格式。按本题规则修改。

## 中文字体交付

中文模板使用 paper/fonts/CJK-Regular.ttf、CJK-Bold.ttf，并在 paper-manifest.files 中声明字体文件和许可。使用可嵌入的、具有中文 Unicode cmap 的 TrueType 字体；不要仅依赖系统字体或外部 Adobe-GB1 映射。示例 write_paper.py 使用 FontTools 从授权源字体按正文制作常规/粗体子集；改正文后重新生成，不能复用子集写另一篇论文。

在 paper-manifest.json 加 unicode_probes 数组，选取真实中文正文短句。编译 helper 使用 pypdf 验证能正确提取这些文字，并检查复合字体的嵌入与 ToUnicode；失败不发布 PDF。它不能代替渲染审查。中文交付应至少使用当前用户预览器所用的渲染器检查；另一渲染器显示正常不能作为兼容性问题已解决的依据。

## compile

从 report 阶段冻结的 paper-manifest.json 编译。只复制声明的源文件、参考文献和图片到独立 build 目录，防止误用旧 PDF。示例（在题目目录执行，脚本路径替换为实际路径）：

```sh
python3 "$WF" run --project . --stage compile --input publication.py --input paper-manifest.json --input paper/main.tex --input paper/body.tex --input figures/result.pdf --output compile-report.json --output report.pdf -- python3 publication.py compile --engine xelatex
```

把 manifest.files 的每一个文件列为 input。自动引擎顺序为 xelatex、tectonic、pdflatex；中文勿选 pdfLaTeX。XeLaTeX/pdfLaTeX 执行三轮，并在首轮后按声明运行 BibTeX/Biber。Tectonic 自行管理轮次；本适配器不支持它与 Biber 的组合。关闭 shell escape，Tectonic 使用 untrusted；这不构成操作系统沙箱。网络下载字体/宏包可能失败，doctor 检测到二进制也不保证依赖齐全。

compile-report.json 包含实际命令、退出码、源文件哈希、日志、错误/警告和 PDF 哈希。非零退出、缺字、未定义引用/命令不通过。Overfull 等警告需结合页面判断。失败时保留日志，修正原因再重试。helper 的新尝试必须使用新的 --build/--output/--report 路径；工作流正式登记仍要求 report.pdf 和 compile-report.json。可先把失败报告移入带编号的历史目录，重新执行，并使用新的 --build；不要把旧成功 PDF 充当新输出。修改论文源时先 reopen report，再生成/登记新版本。

## inspect

```sh
python3 "$WF" run --project . --stage inspect --input publication.py --input report.pdf --output render-manifest.json -- python3 publication.py render
```

默认需要 Poppler 的 pdfinfo、pdftoppm 及中文映射数据。若出现 Missing language pack / Syntax Error，即使退出码为零也拒绝接受；错误保存在渲染目录 renderer.log。可安装 `pypdfium2` 和 `Pillow`，显式加 `--renderer pdfium` 使用 PDFium 独立渲染（同样必须逐页查看）。实际渲染全部页面，默认 110 DPI，上限 100 页可显式调整。render-manifest.json 列出 PDF、各页 PNG 与 SHA256。逐页查看图像，检查缺字、公式、图注、表格、分页和截断，不仅抽取文本。另写 render-review.json：

```json
{"status":"pass","pdf_sha256":"manifest 中 PDF 的哈希","pages":[{"number":1,"sha256":"第 1 页 PNG 哈希","status":"pass","observations":"本页实际观察"}]}
```

pages 必须覆盖每一页，按顺序填写。脚本核对覆盖率与版本，不能替代视觉审查。发现问题按原因 reopen report 或 compile，重编译、重渲染、重新审查。没有实际 PDF 或必要工具不可宣布 PDF 交付完成。理论题同样需要真实编译与渲染证据。
