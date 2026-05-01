"""realign_md_tables: pad markdown tables so source pipes line up vertically. Stdlib only."""
import re,sys
from pathlib import Path
def _split_row(line):
    inner=line.strip()
    if inner.startswith('|'):inner=inner[1:]
    if inner.endswith('|'):inner=inner[:-1]
    return [c.strip() for c in inner.split('|')]
def _is_sep(cells):
    return all(re.match(r'^:?-{1,}:?$',c) for c in cells)
def _sep_align(cells):
    out=[]
    for c in cells:
        left=c.startswith(':');right=c.endswith(':')
        out.append(('right' if right and not left else 'center' if left and right else 'left'))
    return out
def _pad_cell(text,width,align):
    if align=='right':return text.rjust(width)
    if align=='center':
        total=width-len(text);left=total//2;return ' '*left+text+' '*(total-left)
    return text.ljust(width)
def _format_table(rows):
    n_cols=max(len(r) for r in rows)
    rows=[r+['']*(n_cols-len(r)) for r in rows]
    sep_idx=next((i for i,r in enumerate(rows) if _is_sep(r)),-1)
    aligns=_sep_align(rows[sep_idx]) if sep_idx>=0 else ['left']*n_cols
    widths=[0]*n_cols
    for r in rows:
        for i,c in enumerate(r):
            if i==sep_idx:continue
            widths[i]=max(widths[i],len(c))
    widths=[max(w,3) for w in widths]
    out_lines=[]
    for ri,r in enumerate(rows):
        if ri==sep_idx:
            cells=[]
            for i,_ in enumerate(r):
                a=aligns[i] if i<len(aligns) else 'left'
                w=widths[i]
                if a=='right':cells.append('-'*(w+1)+':')
                elif a=='center':cells.append(':'+'-'*w+':')
                else:cells.append('-'*(w+2))
            out_lines.append('| '+ ' | '.join(c.strip() if False else c for c in cells)+' |' if False else '|'+'|'.join(cells)+'|')
        else:
            cells=[_pad_cell(c,widths[i],aligns[i] if i<len(aligns) else 'left') for i,c in enumerate(r)]
            out_lines.append('| '+ ' | '.join(cells)+' |')
    return out_lines
def realign(text):
    lines=text.split('\n')
    out=[];i=0;n=len(lines)
    while i<n:
        if '|' in lines[i] and lines[i].strip().startswith('|'):
            block=[]
            while i<n and lines[i].strip().startswith('|'):
                block.append(lines[i]);i+=1
            rows=[_split_row(b) for b in block]
            try:
                if any(_is_sep(r) for r in rows):
                    out.extend(_format_table(rows))
                    continue
            except Exception:pass
            out.extend(block)
        else:
            out.append(lines[i]);i+=1
    return '\n'.join(out)
def main():
    n=0;changed=0
    for arg in sys.argv[1:]:
        p=Path(arg)
        if not p.exists():print(f'skip {p} (missing)');continue
        original=p.read_text(encoding='utf-8')
        new=realign(original)
        n+=1
        if new!=original:p.write_text(new,encoding='utf-8',newline='\n');print(f'realigned {p}');changed+=1
        else:print(f'unchanged {p}')
    print(f'\n{changed}/{n} files updated')
if __name__=='__main__':sys.exit(main())
