"""Identify the supported patch-chain stages and Chinese versions without changing files."""
from pathlib import Path
import argparse,hashlib,json,zlib
STAGES={
 '3EFA91F18CC6CD012BC213FF421813C113DF51E62F68180CC54C782F21616897':('RS3 Japanese v1.1, headerless',4194304),
 '4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0':('Bokuno Proto1.123 Japanese, headerless',8388608),
 'D3F4B6300D811DC9B707CB85286573E43C2EB93DE729DA990AE5AD09ACE20E0E':('Bokuno simplified Chinese v0.1',8388608),
 'BCE976F8172B5D6F489E0311F44AB8CE2FE644CD14236813EE478DBE22F0D35C':('Bokuno simplified Chinese v0.1.1',8388608),
 '20B421AE2840FB23A40CC7A5B39692781190FE24FC8D1775E0045B7E8FA806F2':('Bokuno simplified Chinese v0.1.2',8388608),
 '26CBE0971C02D2908B486FF40E8616D4E70CB950ADAC8DEEB4632E3F311EAB7F':('Bokuno simplified Chinese v0.1.3',8388608),
}
def identify(path):
 data=Path(path).read_bytes();digest=hashlib.sha256(data).hexdigest().upper();stage=STAGES.get(digest)
 return {'file':Path(path).name,'bytes':len(data),'SHA256':digest,'CRC32':f'{zlib.crc32(data)&0xffffffff:08X}','recognized_stage':stage[0]if stage else None,'possible_512_byte_header':len(data)%32768==512}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('files',nargs='+');args=parser.parse_args()
 for file in args.files:print(json.dumps(identify(file),ensure_ascii=False))
if __name__=='__main__':main()
