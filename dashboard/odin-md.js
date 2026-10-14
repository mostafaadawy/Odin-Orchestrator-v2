/* Odin markdown — lightweight renderer for chat replies + a speech cleaner.
   OdinMD.render(el, rawMarkdown)  -> renders tables, **bold**, *italic*, `code`, lists,
                                      headers, links, and ``` code blocks (with copy).
   OdinMD.toSpeech(rawMarkdown)    -> plain text for TTS (no **, |, #, code blocks). */
window.OdinMD = (function () {
  function esc(s){ return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

  function inline(s){
    s = esc(s);
    s = s.replace(/`([^`]+)`/g, '<code class="ic">$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>');
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  }

  function splitRow(line){ return line.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|').map(x=>x.trim()); }

  function render(el, raw){
    const lines = (raw||"").replace(/\r/g,"").split("\n");
    let i=0; const out=[];
    while(i<lines.length){
      const line = lines[i];

      if(/^```/.test(line)){                                    // code block
        const lang = line.replace(/^```/,'').trim();
        const code=[]; i++;
        while(i<lines.length && !/^```/.test(lines[i])){ code.push(lines[i]); i++; }
        i++;
        const id='c'+Math.random().toString(36).slice(2,8);
        out.push('<pre class="code"><div class="cphdr"><span>'+(lang||'shell')+
          '</span><button data-copy="'+id+'">copy</button></div><code id="'+id+'">'+
          esc(code.join("\n"))+'</code></pre>');
        continue;
      }

      if(/\|/.test(line) && i+1<lines.length && /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(lines[i+1])){ // table
        const head = splitRow(line); i+=2; const rows=[];
        while(i<lines.length && lines[i].includes('|') && lines[i].trim()!==''){ rows.push(splitRow(lines[i])); i++; }
        let t='<table class="md"><thead><tr>'+head.map(h=>'<th>'+inline(h)+'</th>').join('')+'</tr></thead><tbody>';
        rows.forEach(r=>{ t+='<tr>'+r.map(c=>'<td>'+inline(c)+'</td>').join('')+'</tr>'; });
        out.push(t+'</tbody></table>');
        continue;
      }

      const h = line.match(/^(#{1,6})\s+(.*)$/);                // header
      if(h){ const lvl=Math.min(h[1].length+2,6); out.push('<h'+lvl+' class="md">'+inline(h[2])+'</h'+lvl+'>'); i++; continue; }

      if(/^\s*([-*+]|\d+\.)\s+/.test(line)){                    // list
        const ordered=/^\s*\d+\./.test(line); const items=[];
        while(i<lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])){ items.push(lines[i].replace(/^\s*([-*+]|\d+\.)\s+/,'')); i++; }
        out.push('<'+(ordered?'ol':'ul')+' class="md">'+items.map(x=>'<li>'+inline(x)+'</li>').join('')+'</'+(ordered?'ol':'ul')+'>');
        continue;
      }

      if(line.trim()===''){ i++; continue; }

      const para=[line]; i++;                                   // paragraph
      while(i<lines.length && lines[i].trim()!=='' && !/^```/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i])
            && !/^\s*([-*+]|\d+\.)\s+/.test(lines[i]) && !lines[i].includes('|')){ para.push(lines[i]); i++; }
      out.push('<p class="md">'+inline(para.join(' '))+'</p>');
    }
    el.innerHTML = out.join('');
    el.querySelectorAll('button[data-copy]').forEach(b=>{
      b.onclick=()=>{ const c=el.querySelector('#'+b.getAttribute('data-copy')); if(c) navigator.clipboard.writeText(c.textContent); };
    });
  }

  function toSpeech(raw){
    let s = raw||"";
    s = s.replace(/```[\s\S]*?```/g, ' . ');     // never read code aloud
    s = s.replace(/`([^`]+)`/g, '$1');
    s = s.replace(/\*\*([^*]+)\*\*/g, '$1');
    s = s.replace(/__([^_]+)__/g, '$1');
    s = s.replace(/\*([^*\n]+)\*/g, '$1');
    s = s.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    s = s.replace(/^#{1,6}\s+/gm, '');
    s = s.replace(/^\s*([-*+]|\d+\.)\s+/gm, '');
    s = s.replace(/^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/gm, '');      // table separator rows
    s = s.replace(/\|/g, ', ');                                  // table cells
    s = s.replace(/[ \t]{2,}/g, ' ').replace(/\n{2,}/g, '. ').trim();
    return s;
  }

  return { render: render, toSpeech: toSpeech };
})();
