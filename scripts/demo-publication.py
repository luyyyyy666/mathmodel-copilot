#!/usr/bin/env python3
"""Publication demo. Stops for actual figure/page inspection; never auto-approves visual quality."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / '.agents/skills/mathmodel-workflow'
WF = BUNDLE / 'scripts/workflow.py'
FIXTURE = ROOT / 'examples/facility-location'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--engine', choices=['auto','xelatex','pdflatex','tectonic'], default='auto')
    parser.add_argument('--renderer', choices=['poppler','pdfium'], default='poppler')
    parser.add_argument('--font', help='Licensed Chinese TrueType font, optionally variable wght')
    parser.add_argument('--font-license', help='License file supplied with the font')
    args = parser.parse_args()
    project = Path(args.project).resolve()

    def cli(*items):
        p = subprocess.run([sys.executable,str(WF),items[0],'--project',str(project),*items[1:]],capture_output=True,text=True)
        if p.returncode:
            raise RuntimeError(p.stderr or p.stdout)
        return json.loads(p.stdout)

    def execute(stage, inputs, outputs, argv):
        items=['run','--stage',stage,'--timeout','600']
        for p in inputs: items+=['--input',p]
        for p in outputs: items+=['--output',p]
        return cli(*items,'--',*argv)['id']

    def previous(stage):
        records=[json.loads(p.read_text()) for p in (project/'.workflow/executions').glob('*.json')]
        revision=cli('status')['revision']
        records=[r for r in records if r['stage']==stage and r['status']=='succeeded' and r['revision']==revision]
        return max(records,key=lambda r:r['started_at'])['id'] if records else None

    def wait_for_review(name):
        print(json.dumps({'project':str(project),'needs_visual_review':name,
              'instruction':'Inspect actual images, write version-bound observations as described in the Skill, then rerun this command.',
              'model_calls':0},ensure_ascii=False,indent=2))

    if not (project/'.workflow/state.json').exists():
        subprocess.run([sys.executable,str(ROOT/'scripts/demo-workflow.py'),'--project',str(project),
                        '--destination',args.destination,'--publication'],check=True,capture_output=True)
        for name in ['figures.py','write_paper.py']:
            shutil.copyfile(FIXTURE/name,project/name)
        for src,name in [(BUNDLE/'assets/figures/matplotlib_templates.py','matplotlib_templates.py'),
                         (BUNDLE/'assets/figures/LICENSE','MATHODOLOGY-LICENSE'),
                         (BUNDLE/'assets/figures/provenance.json','figure-template-provenance.json'),
                         (BUNDLE/'assets/latex/main-zh.tex','main-zh.tex'),
                         (BUNDLE/'scripts/publication.py','publication.py')]:
            shutil.copyfile(src,project/name)
    state=json.loads((project/'.workflow/state.json').read_text())
    if state['format']!=2 or not state['require_pdf']:
        raise ValueError('Use a v2 PDF project; this demo does not alter existing project requirements')
    stage=cli('next')['next']
    if stage and stage['id']=='figures':
        ident=previous('figures')
        if not ident:
            outputs=['figure-manifest.json','environment.txt','results/sensitivity.json','results/sensitivity-checks.json']
            outputs += [f'figures/{n}.{ext}' for n in ['distances','comparison','sensitivity'] for ext in ['png','pdf']]
            ident=execute('figures',['figures.py','matplotlib_templates.py','solve.py','verify.py','inputs/01-data.json',
                            'results/baseline.json','results/candidate.json'],outputs,[sys.executable,'figures.py'])
        if not (project/'figure-review.json').exists():
            wait_for_review('figure-review.json');return
        cli('complete','--stage','figures','--execution',ident,'--artifact','MATHODOLOGY-LICENSE','--artifact','figure-template-provenance.json')
    stage=cli('next')['next']
    if stage and stage['id']=='report':
        if not (project/'chinese-font.ttf').exists() or not (project/'font-license.txt').exists():
            if not args.font or not args.font_license:
                print(json.dumps({'needs_font_source':'Supply --font FONT.ttf --font-license OFL.txt; see quickstart.'}));return
            shutil.copyfile(Path(args.font).resolve(),project/'chinese-font.ttf')
            shutil.copyfile(Path(args.font_license).resolve(),project/'font-license.txt')
        ident=previous('report') or execute('report',['write_paper.py','main-zh.tex','chinese-font.ttf','font-license.txt','figure-manifest.json',
                     'results/baseline.json','results/candidate.json','results/sensitivity.json','results/sensitivity-checks.json'],
                    ['report.md','paper-manifest.json','paper/main.tex','paper/sections/abstract.tex','paper/sections/body.tex','paper/fonts/CJK-Regular.ttf','paper/fonts/CJK-Bold.ttf','paper/fonts/OFL.txt'],
                    [sys.executable,'write_paper.py'])
        cli('complete','--stage','report','--execution',ident)
    stage=cli('next')['next']
    if stage and stage['id']=='compile':
        paper=json.loads((project/'paper-manifest.json').read_text())
        ident=previous('compile')
        if not ident:
            # Failed attempts retain their logs; successful or unrecognized outputs are never overwritten.
            failed_report=project/'compile-report.json'
            if failed_report.exists():
                failed=json.loads(failed_report.read_text())
                if failed.get('status')!='failed' or (project/'report.pdf').exists():
                    raise ValueError('Existing compilation output needs inspection before retry')
                archive=project/'build'/f'failed-compile-{len(list((project/".workflow/executions").glob("*.json")))}.json'
                if archive.exists():
                    raise ValueError('Failure archive already exists')
                archive.parent.mkdir(parents=True,exist_ok=True)
                failed_report.rename(archive)
            attempt=1
            while (project/f'build/latex-{attempt}').exists(): attempt+=1
            ident=execute('compile',['publication.py','paper-manifest.json',*paper['files']],
                          ['compile-report.json','report.pdf'],[sys.executable,'publication.py','compile',
                          '--engine',args.engine,'--timeout','500','--build',f'build/latex-{attempt}'])
        cli('complete','--stage','compile','--execution',ident)
    stage=cli('next')['next']
    if stage and stage['id']=='inspect':
        ident=previous('inspect') or execute('inspect',['publication.py','report.pdf'],['render-manifest.json'],
                        [sys.executable,'publication.py','render','--renderer',args.renderer])
        if not (project/'render-review.json').exists():
            wait_for_review('render-review.json');return
        cli('complete','--stage','inspect','--execution',ident)
    stage=cli('next')['next']
    if stage and stage['id']=='deliver':
        (project/'REPRODUCE.md').write_text('''# Reproduce the synthetic facility-location example

Python 3.10+; NumPy, Matplotlib and a configured LaTeX engine; Poppler for PDF rendering.
Exact local numerical versions are in environment.txt. This demo used only synthetic data and no model API.

In a copy of this delivery, run `python3 reproduce.py replay.json` for a fresh-directory numerical replay.
For plots run `python3 figures.py`; it regenerates PNG/PDF from checked data, including p=1..4 scenarios.
For paper sources run `python3 write_paper.py`.
For a new PDF run `python3 publication.py compile --engine auto --output replay.pdf --report replay-compile.json --build build/replay`.
For page images use configured Poppler language data or install pypdfium2 and add --renderer pdfium. Run `python3 publication.py render --pdf replay.pdf --output-dir render/replay --report replay-render.json`.
Inspect each actual figure and page; the helper does not perform semantic or visual acceptance.

Compilation commands and logs are in compile-report.json. Use the same engine and dependencies when comparing layout.
Numerical reproduction compares fresh output with registered results. PDF byte identity is not guaranteed across toolchains.
A,C gives 16 weighted km at p=2. This does not establish validity for real cities or uncertain inputs.
Mathodology plotting template license and provenance are included. No external scientific citations were fabricated.
''',encoding='utf-8')
        ident=previous('deliver') or execute('deliver',['reproduce.py','solve.py','verify.py','inputs/01-data.json',
                       'results/baseline.json','results/candidate.json'],['results/reproduction.json'],
                       [sys.executable,'reproduce.py','results/reproduction.json'])
        cli('complete','--stage','deliver','--execution',ident)
    cli('check')
    result=cli('export','--destination',str(Path(args.destination).resolve()))
    result['model_calls']=0
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
