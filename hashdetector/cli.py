from argparse import ArgumentParser
from datetime import datetime,timezone
from json import dumps
from pathlib import Path
from sys import exit,stderr
from . import LOGO,VERSION
from .core import detect
LOG_FILE=None
DEBUG=False
def setup_logs(path=None,debug=False):
    global LOG_FILE,DEBUG
    LOG_FILE=path
    DEBUG=debug
    if not LOG_FILE:
        return
    try:
        open(LOG_FILE,"a",encoding="utf-8").close()
    except OSError as e:
        print(f"Log file error: {LOG_FILE}: {e}",file=stderr)
        exit(2)
def log_event(event,**data):
    if not LOG_FILE:
        return
    record={"time":datetime.now(timezone.utc).isoformat(),"event":event,**data}
    try:
        open(LOG_FILE,"a",encoding="utf-8").write(dumps(record,ensure_ascii=False)+"\n")
    except OSError as e:
        print(f"Log write error: {LOG_FILE}: {e}",file=stderr)
        exit(2)
def result(value,line=None,strict=False,top=None):
    matches=detect(value,strict,top)
    data={"input":value,"found":bool(matches),"matches":matches}
    if line is not None:
        data={"line":line,**data}
    return data
def render_json(data):
    return dumps(data,indent=2)
def banner():
    print(LOGO)
def menu():
    return "\n".join(("1) HASH","2) File Directory","3) Exit"))
def clean_path(value):
    return value.strip().strip('"').strip("'")
def direct_path(value):
    path=Path(clean_path(value)).expanduser()
    return str(path) if path.is_absolute() else None
def render_text(input_value,matches,label=None,hidden=0,quiet=False):
    out=[]
    if label:
        out.append(label)
    if not matches:
        out.append("\nNot Found.")
        return "\n".join(out)
    out.append("\nPossible Hashes:")
    for hit in matches:
        line=f"[{hit['score']}] {hit['name']}"
        detail=f"hashcat={hit['hashcat']} | john={hit['john']} | {' | '.join(hit['reasons'])}"
        out.append(line if quiet else f"{line} | {detail}")
    if hidden:
        out.append(f"\nHidden Matches: {hidden}")
    return "\n".join(out)
def show(value,label=None,strict=False,top=5,quiet=False):
    hits=detect(value,strict)
    print(render_text(value,hits[:top],label,len(hits)-min(len(hits),top),quiet))
def read_file(path):
    try:
        return open(path,encoding="utf-8-sig",errors="replace").read().splitlines()
    except FileNotFoundError:
        log_event("file_not_found",path=path)
        print(f"File not found: {path}",file=stderr)
        exit(2)
    except OSError as e:
        log_event("file_read_error",path=path,error=str(e))
        print(f"File read error: {path}: {e}",file=stderr)
        exit(2)
def file_results(path,strict=False,top=None):
    return [
    result(line.strip(),number,strict,top)
    for number,line in enumerate(read_file(path),1)
    if line.strip()
    ]
def file_mode(path,json_mode=False,strict=False,top=5,quiet=False,with_banner=True):
    items=file_results(path,strict,top if json_mode else None)
    log_event("file_mode",path=path,json=json_mode,items=len(items))
    if json_mode:
        print(render_json(items))
        return
    if with_banner:
        banner()
    seen=False
    for item in items:
        if seen:
            print("-"*50)
        label=f"line {item['line']}: {item['input']}"
        hidden=len(item["matches"])-min(len(item["matches"]),top)
        print(render_text(item["input"],item["matches"][:top],label,hidden,quiet))
        seen=True
def parser():
    p=ArgumentParser(prog="LOYA Hash Detector",description="Identify hash formats from one hash or a file.")
    p.add_argument("hash",nargs="?",help="hash value to identify")
    p.add_argument("-f","--file",help="file with one hash per line")
    p.add_argument("--json",action="store_true",help="print JSON output")
    p.add_argument("--top",type=int,default=5,help="maximum matches to show")
    p.add_argument("--strict",action="store_true",help="hide weak matches when stronger matches exist")
    p.add_argument("--quiet",action="store_true",help="hide match details in text output")
    p.add_argument("--version",action="store_true",help="print version and exit")
    p.add_argument("--log-file",help="append operational logs to a JSONL file")
    p.add_argument("--debug",action="store_true",help="show unexpected exceptions")
    return p
def hash_mode(value,args):
    data=result(value,None,args.strict,None)
    log_event("detect",input=value,found=data["found"],matches=len(data["matches"]))
    shown=data["matches"][:args.top]
    print(render_text(value,shown,None,len(data["matches"])-len(shown),args.quiet))
def interactive(args):
    banner()
    while True:
        try:
            print("-"*50)
            print(menu())
            choice=input("OPTION: ").strip()
            if choice=="1":
                hash_mode(input("HASH: ").strip(),args)
            elif choice=="2":
                file_mode(clean_path(input("FILE DIRECTORY: ")),False,args.strict,args.top,args.quiet,False)
            elif choice=="3":
                log_event("stop")
                print("Bye!")
                exit()
            else:
                log_event("invalid_option",choice=choice)
                print("Invalid option.")
        except (KeyboardInterrupt,EOFError):
            log_event("stop")
            print("\nBye!")
            exit()
def run(p,args):
    setup_logs(args.log_file,args.debug)
    log_event("start",json=args.json,file=bool(args.file),hash=bool(args.hash),top=args.top,strict=args.strict)
    if args.version:
        print(VERSION)
        log_event("version",version=VERSION)
        return
    if args.top<1:
        p.error("--top must be 1 or greater")
    if args.hash and args.file:
        p.error("use a hash or --file, not both")
    if args.file:
        file_mode(args.file,args.json,args.strict,args.top,args.quiet)
        return
    if args.hash:
        direct=direct_path(args.hash)
        if direct:
            file_mode(direct,args.json,args.strict,args.top,args.quiet)
            return
        if args.json:
            data=result(args.hash,None,args.strict,args.top)
            log_event("detect",input=args.hash,found=data["found"],matches=len(data["matches"]))
            print(render_json(data))
            return
        banner()
        print("-"*50)
        hash_mode(args.hash,args)
        return
    if args.json:
        p.error("--json requires a hash or --file")
    interactive(args)
def main():
    p=parser()
    args=p.parse_args()
    try:
        run(p,args)
    except SystemExit:
        raise
    except Exception as e:
        log_event("error",error=repr(e))
        if DEBUG:
            raise
        print(f"Error: {e}",file=stderr)
        exit(1)
