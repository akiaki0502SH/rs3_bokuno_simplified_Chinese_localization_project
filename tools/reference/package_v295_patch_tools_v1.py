"""Package the verified local v295 patches with unmodified official Flips v198."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / 'artifacts/patches'
NAME = 'bokuno_cn_v295_Proto1.123_20261017_01'
BUNDLE = OUT / (NAME + '_patch_and_flips')
BUNDLE_ZIP = OUT / (BUNDLE.name + '.zip')
TOOL_ZIP = OUT / 'Flips-v198-windows-with-source_20261017_01.zip'
QA = ROOT / 'qa/patch_tools_v295_20261017_01'
RECEIPT = ROOT / 'qa/V295_PATCH_TOOLS_PACKAGE_20261017_01.json'
HANDOFF = ROOT / 'docs/PATCH_TOOLS_V295_20261017_01.md'
SOURCE_MANIFEST = ROOT / 'text/translations/translation_sources_current.json'

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()

def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

for path in (BUNDLE, BUNDLE_ZIP, TOOL_ZIP, QA, RECEIPT, HANDOFF):
    assert path.resolve().is_relative_to(Path('G:/CodexProjects').resolve())
    assert path.resolve().is_relative_to(ROOT)
    assert not path.exists(), f'Refusing to overwrite: {path}'

manifest = read_json(SOURCE_MANIFEST)
chain = read_json(ROOT / 'qa/TRANSLATION_PATCH_CHAIN_V295_20261017_01.json')
proof = read_json(ROOT / 'qa/V295_TESTPACKAGE32_PROOF_20261017_01.json')
assert manifest['build_revision'] == chain['build_revision'] == 'v295_inn_price_padding01'
rom = ROOT / manifest['latest_test_ROM']['file']
expected = manifest['latest_test_ROM']['SHA256']
assert sha(rom) == expected == chain['output_ROM_SHA256'] == proof['ROM_SHA256']
assert chain['status'] == 'COMPLETE_RS3_BOKUNO_CN_CHAIN_BYTE_IDENTICAL_PASS'
pure_zip = ROOT / chain['ZIP']
assert sha(pure_zip) == chain['ZIP_SHA256']
base = WORKSPACE / 'roms/source/bokuno_proto_1.123_analysis.sfc'
base_sha = '4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
assert sha(base) == base_sha
original = WORKSPACE / 'roms/source/rs3_v1.1_original_analysis.sfc'
original_sha = sha(original)
public_manifest = json.dumps(manifest['latest_public_release'], ensure_ascii=False, sort_keys=True)
flips_source = WORKSPACE / 'github_public_release/third_party/Flips'
audit = read_json(ROOT / 'qa/release_v0_1_3_preparation_20261017_01/public_release_audit.json')
flips_files = [row for row in audit['repo_files'] if row['file'].startswith('third_party/Flips/')]
assert len(flips_files) == 6
for row in flips_files:
    assert sha(WORKSPACE / 'github_public_release' / row['file']) == row['SHA256']

BUNDLE.mkdir()
QA.mkdir()
for row in chain['patches']:
    source = ROOT / chain['directory'] / row['file']
    assert sha(source) == row['SHA256']
    shutil.copy2(source, BUNDLE / row['file'])
for name in ('补丁链验证.json', 'SHA256_补丁校验.txt'):
    shutil.copy2(ROOT / chain['directory'] / name, BUNDLE / name)
for row in flips_files:
    dest = BUNDLE / row['file']
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE / 'github_public_release' / row['file'], dest)
shutil.copy2(WORKSPACE / 'github_public_release/NOTICE.md', BUNDLE / 'NOTICE.md')
readme = '''Bokuno Proto1.123 简体中文补丁 v295（对应测试包32）

本版包含：标题开场序文汉化、数字0—9字形与定位修正、住宿报价前导空格修正，以及此前已合入的汉化内容。
实际游玩验收仍在进行。

【已有日文 Bokuno Proto1.123 ROM】
1. 将整个压缩包解压到一个文件夹。
2. 打开 third_party/Flips/flips.exe。
3. 点击 Apply Patch，选择 bokuno_cn_v295_for_Proto1.123.bps（推荐）。
4. 选择日文 Bokuno Proto1.123 ROM，另存为一个新的汉化 ROM。
5. 用模拟器打开新 ROM。

IPS 与 BPS 内容相同，二选一即可。
本补丁的底片必须是日文 Bokuno Proto1.123，大小 8,388,608 字节。
请勿在旧汉化 ROM 上直接叠加本补丁。

【只有日文 RS3 原版 ROM】
先准备日文《Romancing SaGa 3》v1.1，无512字节拷贝器头，大小 4,194,304 字节。
使用自行取得的作者原始 ぼくのProto1.123.ips 打成日文 Bokuno Proto1.123，再按上述步骤应用本包汉化 BPS。
顺序：日文RS3 v1.1 → 作者Bokuno Proto1.123补丁 → 本包汉化补丁。
每一步均另存新文件，保留原文件。

【校验】
日文 RS3 v1.1 CRC32：6C50C2CF
日文 Bokuno Proto1.123 CRC32：7E165025
v295 汉化输出 CRC32：741F6A65
v295 汉化输出 SHA256：
98168405A376F9353DF6F93CF7D70B63E667B46B8CCDE278EE588DDD6E02D476

本包 IPS、BPS 均已实际应用，与当前 v295／包32 的 ROM 逐字节一致。
BPS 会核对底片，若提示不匹配，请核对底片版本。

【工具与分发】
本包不含 ROM、存档或作者原始 Bokuno 补丁。
Flips v198 为官方 Windows 程序，原许可证、对应源码和来源说明在 third_party/Flips 中。
其中 Flips-v198-source.zip 是工具源码，普通使用无需解压或编译。
汉化补丁使用及转载声明见 NOTICE.md。
'''
(BUNDLE / 'README_先看这里.txt').write_text(readme, encoding='utf-8-sig')

flips = BUNDLE / 'third_party/Flips/flips.exe'
applications = []
for row in chain['patches']:
    patch = BUNDLE / row['file']
    target = QA / ('applied_' + patch.suffix[1:] + '.sfc')
    proc = subprocess.run([str(flips), '--apply', str(patch), str(base), str(target)], capture_output=True, timeout=180)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert target.read_bytes() == rom.read_bytes()
    applications.append({'patch': patch.name, 'exit_code': proc.returncode, 'output_ROM_SHA256': sha(target), 'byte_identical_to_package32': True})

def create_zip(path: Path, rows):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in rows:
            archive.writestr(name, content)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for name, content in rows:
            assert archive.read(name) == content

bundle_rows = [(p.relative_to(BUNDLE).as_posix(), p.read_bytes()) for p in sorted(BUNDLE.rglob('*')) if p.is_file()]
create_zip(BUNDLE_ZIP, bundle_rows)
tool_readme = '''Flips v198 Windows 打补丁工具

解压后打开 third_party/Flips/flips.exe，点击 Apply Patch。
先选择补丁文件（.bps 或 .ips），再选择对应的原始 ROM，最后另存新的 ROM。

应用本项目 v295 汉化补丁时，请选择日文 Bokuno Proto1.123 作为底片；推荐使用 BPS。
本工具包不含汉化补丁或 ROM。

工具官方来源、许可、对应源码：third_party/Flips/README.md、COPYING、COPYING.gpl3、Flips-v198-source.zip。
源码包普通使用无需解压或编译。
'''
tool_rows = [(name, content) for name, content in bundle_rows if name.startswith('third_party/Flips/')]
tool_rows.append(('README_工具使用说明.txt', tool_readme.encode('utf-8-sig')))
create_zip(TOOL_ZIP, tool_rows)

forbidden = {'.sfc', '.smc', '.srm', '.state', '.sav', '.ttf', '.otf', '.woff', '.woff2'}
def audit_zip(raw: bytes):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            name = entry.filename
            suffix = Path(name).suffix.lower()
            assert suffix not in forbidden and not (len(suffix) == 4 and suffix[1:].isdigit()), name
            content = archive.read(entry)
            if suffix == '.exe':
                assert name == 'third_party/Flips/flips.exe'
                assert hashlib.sha256(content).hexdigest().upper() == sha(flips)
            if suffix == '.zip':
                audit_zip(content)
for archive in (BUNDLE_ZIP, TOOL_ZIP, pure_zip):
    audit_zip(archive.read_bytes())
assert sha(base) == base_sha and sha(original) == original_sha and sha(rom) == expected

receipt = {
    'status': 'V295_PATCH_AND_FLIPS_PACKAGE_VERIFIED_PASS',
    'build_revision': manifest['build_revision'],
    'corresponds_to_private_test_package': 32,
    'output_ROM_SHA256': expected,
    'patch_chain_validation': 'qa/TRANSLATION_PATCH_CHAIN_V295_20261017_01.json',
    'bundled_tool_apply_tests': applications,
    'Flips_version': 'v198',
    'Flips_executable_SHA256': sha(flips),
    'Flips_files_match_previous_official_distribution': True,
    'archives': [{'file': rel(p), 'bytes': p.stat().st_size, 'SHA256': sha(p)} for p in (BUNDLE_ZIP, pure_zip, TOOL_ZIP)],
    'ZIP_integrity_and_full_readback': True,
    'recursive_archive_audit_no_ROM_saves_or_fonts': True,
    'original_ROM_inputs_unchanged': True,
    'public_release_unchanged': True,
    'no_Git_commit_push_or_publication': True,
}
write_json(RECEIPT, receipt)
HANDOFF.write_text('''# v295 补丁与 Flips 本地打包记录

本次仅整理本地分发包，对应 v295 / 私人测试包32。ROM和原存档未修改，未提交、推送或发布新GitHub版本。

- 整合包：`''' + rel(BUNDLE_ZIP) + '''`
- 纯补丁：`''' + rel(pure_zip) + '''`
- 工具包：`''' + rel(TOOL_ZIP) + '''`
- 验证记录：`''' + rel(RECEIPT) + '''`

完整原版RS3→日文Bokuno→汉化链通过；整合包内的Flips分别应用IPS/BPS，与当前v295 ROM逐字节一致。ZIP完整读回与嵌套文件检查通过，分发包不含ROM、私人存档或字体文件。

正确顺序：日文RS3 v1.1无头原版→作者Proto1.123补丁→本包汉化BPS或IPS（二选一）。已有日文Bokuno Proto1.123可直接应用汉化补丁。实际游玩验收状态仍以v295主交接文档为准。
''', encoding='utf-8')
manifest['latest_translation_patch_handoff'] = rel(HANDOFF)
manifest['latest_translation_patch_tools_package'] = {**receipt['archives'][0], 'validation': rel(RECEIPT), 'Flips_version': 'v198', 'standalone_tool': receipt['archives'][2]}
assert json.dumps(manifest['latest_public_release'], ensure_ascii=False, sort_keys=True) == public_manifest
write_json(SOURCE_MANIFEST, manifest)
print(json.dumps(receipt, ensure_ascii=False, indent=2))

