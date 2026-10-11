"""Read IPS record boundaries and sizes; no ROM input is required."""
from pathlib import Path
import argparse,json
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('patch');args=parser.parse_args();data=Path(args.patch).read_bytes()
 if not data.startswith(b'PATCH'):raise SystemExit('Not an IPS file')
 i=5;records=literal=rle=0;maximum=0
 while data[i:i+3]!=b'EOF':
  if i+5>len(data):raise SystemExit('Truncated IPS header')
  offset=int.from_bytes(data[i:i+3],'big');length=int.from_bytes(data[i+3:i+5],'big');i+=5
  if length:
   if i+length>len(data):raise SystemExit('Truncated IPS payload')
   i+=length;literal+=length
  else:
   if i+3>len(data):raise SystemExit('Truncated IPS RLE')
   length=int.from_bytes(data[i:i+2],'big');i+=3;rle+=length
  records+=1;maximum=max(maximum,offset+length)
 i+=3;tail=data[i:]
 if len(tail)not in[0,3]:raise SystemExit('Unexpected IPS trailer')
 print(json.dumps({'records':records,'literal_bytes':literal,'rle_output_bytes':rle,'highest_output_byte_exclusive':maximum,'optional_truncate_size':int.from_bytes(tail,'big')if tail else None}))
if __name__=='__main__':main()
