(function (global) {
  "use strict";
  if (global.LimeAI) return;

  const state = { config: null, messages: [], sessionId: null, busy: false };
  const defaultIcons = {
    chat: '<svg viewBox="0 0 24 24"><path d="M20 15a3 3 0 0 1-3 3H8l-5 3V6a3 3 0 0 1 3-3h11a3 3 0 0 1 3 3z"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18"/></svg>',
    send: '<svg viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4zM22 2 11 13"/></svg>'
  };

  const css = `
    :host{--lime:#00871e;--lime-hover:#006417;--dark:#132019;--muted:#68746d;--surface:#fff;--radius:1rem;--button-radius:.75rem;--message-radius-compact:.65rem;--border-color:#e1e3e2;--border:1px solid var(--border-color);--shadow:0 18px 55px #10281938;font:14px/1.45 Inter,system-ui,-apple-system,sans-serif;color:var(--dark)}
    *{box-sizing:border-box}.fab{position:fixed;right:22px;bottom:22px;width:60px;height:60px;border:0;border-radius:var(--button-radius);background:var(--lime);color:#fff;cursor:pointer;display:grid;place-items:center;opacity:1;transform:scale(1);transition:background-color .2s,opacity .16s ease,transform .24s ease;z-index:2147483647}.fab:hover{background:var(--lime-hover)}svg{width:24px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.fab img{width:24px;height:24px}.send img{width:19px;height:19px}.x img{width:18px;height:18px}.logo img{width:24px;height:24px}img{display:block;object-fit:contain}
    .panel{position:fixed;right:22px;bottom:22px;width:min(390px,calc(100vw - 24px));height:min(650px,calc(100vh - 44px));background:#f8faf7;border:var(--border);border-radius:var(--button-radius);box-shadow:var(--shadow);overflow:hidden;display:flex;flex-direction:column;opacity:0;visibility:hidden;pointer-events:none;transform:scale(.12);transform-origin:calc(100% - 30px) calc(100% - 30px);transition:transform .44s cubic-bezier(.22,.8,.25,1),opacity .14s ease,border-radius .3s ease,visibility 0s linear .44s;z-index:2147483646}.panel.open{opacity:1;visibility:visible;pointer-events:auto;transform:scale(1);border-radius:var(--radius);transition:transform .44s cubic-bezier(.22,.8,.25,1),opacity .12s ease,border-radius .3s ease,visibility 0s}.panel.open~.fab{opacity:0;transform:scale(.72);pointer-events:none}
    header{background:var(--lime);color:#fff;padding:19px 20px;display:flex;align-items:center;gap:12px}.logo{width:38px;height:38px;flex:0 0 38px;background:var(--lime);color:var(--dark);display:grid;place-items:center;font-weight:900}.logo img{width:38px;height:38px;border-radius:0;object-fit:contain}.title{flex:1}.title b{display:block;font-size:15px}.title span{font-size:12px;color:#fff;opacity:.82}.x{width:32px;height:32px;border:0;color:#fff;background:transparent;cursor:pointer;padding:7px;border-radius:50%;display:grid;place-items:center;transition:background-color .18s}.x:hover{background:#ffffff24}.x svg{width:18px}
    .messages{flex:1;overflow:auto;padding:18px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth}.msg{width:fit-content;max-width:86%;padding:11px 13px;border-radius:var(--radius);white-space:pre-wrap;overflow-wrap:anywhere;text-wrap:pretty}.msg.single-line{border-radius:var(--message-radius-compact)}.bot{align-self:flex-start;background:var(--surface);border:var(--border)}.user{align-self:flex-end;background:var(--lime);color:#fff}.text-link{color:var(--lime-hover);font-weight:600;text-decoration:underline;text-underline-offset:2px}.user .text-link{color:#fff}.sources{font-size:11px;margin-top:8px;padding-top:8px;border-top:var(--border)}.sources a{display:block;color:#3c6814;text-decoration:none;margin-top:4px}.actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}.action-link{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:8px 12px;border-radius:var(--button-radius);background:var(--lime);color:#fff;text-decoration:none;font-size:12px;font-weight:600;line-height:1.2;transition:background-color .18s}.action-link:hover{background:var(--lime-hover)}.typing{display:flex;gap:5px;padding:14px}.typing i{width:6px;height:6px;border-radius:50%;background:#8b968e;animation:pulse 1s infinite}.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}@keyframes pulse{50%{opacity:.25;transform:translateY(-2px)}}
    form{padding:13px;background:var(--surface);border-top:var(--border);display:flex;gap:9px;align-items:flex-end}textarea{font:inherit;resize:none;max-height:110px;min-height:43px;flex:1;border:var(--border);border-radius:var(--button-radius);padding:11px 12px;outline:0}textarea:focus{border-color:#c9cdcb}.send{width:43px;height:43px;border:0;border-radius:var(--button-radius);background:var(--lime);display:grid;place-items:center;cursor:pointer;transition:background-color .2s}.send:hover:not(:disabled){background:var(--lime-hover)}.send:disabled{opacity:.45;cursor:default}.send svg{width:19px}
    .note{padding:0 16px 10px;background:var(--surface);color:#89928d;font-size:10px;text-align:center}
    .coach{position:fixed;right:22px;bottom:96px;width:390px;padding:19px;border-radius:var(--radius);background:var(--surface);color:var(--dark);box-shadow:var(--shadow);z-index:2147483647}.coach:after{content:"";position:absolute;right:22px;bottom:-8px;width:16px;height:16px;background:var(--surface);transform:rotate(45deg)}.coach b{display:block;margin-bottom:6px;font-size:14px;color:var(--lime)}.coach span{display:block;font-size:14px;line-height:1.45;color:#465149}.coach-action{position:relative;width:100%;margin-top:14px;padding:8px 15px;border:0;border-radius:var(--button-radius);background:var(--lime);color:#fff;font:inherit;font-weight:500;cursor:pointer;transition:background-color .18s}.coach-action:hover{background:var(--lime-hover)}.coach-backdrop{position:fixed;inset:0;background:#09140c66;z-index:2147483645}
    @media(max-width:520px){.panel{inset:0;width:100vw;height:100dvh;max-height:none;border:0;transform:scale(.08);transform-origin:calc(100% - 45px) calc(100% - 45px)}.panel.open{transform:scale(1);border-radius:0}.fab{right:15px;bottom:15px}.coach{right:14px;bottom:88px;width:calc(100vw - 28px)}header{padding-top:max(18px,env(safe-area-inset-top))}}
    @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
  `;

  function esc(value) { const d=document.createElement("div"); d.textContent=value; return d.innerHTML; }
  function scrollToBottom(){
    const messages=state.ui?.messages;
    if(!messages) return;
    messages.scrollTop=messages.scrollHeight;
    requestAnimationFrame(()=>{messages.scrollTop=messages.scrollHeight});
  }
  function iconMarkup(name) {
    const source=state.config.icons?.[name];
    if(!source) return defaultIcons[name]||"";
    try {
      const url=new URL(source,document.baseURI);
      const safe=["http:","https:","blob:"].includes(url.protocol)||(url.protocol==="data:"&&/^data:image\//i.test(source));
      return safe?`<img src="${esc(url.href)}" alt="">`:(defaultIcons[name]||"");
    } catch (_) { return defaultIcons[name]||""; }
  }
  function linkifyMessage(item){
    const text=item.textContent, pattern=/(https?:\/\/[^\s]+|(?:[a-z0-9-]+\.)+(?:tv|ru|com|net|org)(?:\/[^\s]*)?)/gi;
    const fragment=document.createDocumentFragment(); let index=0, match;
    while((match=pattern.exec(text))){
      fragment.append(document.createTextNode(text.slice(index,match.index)));
      let value=match[0], tail="";
      while(/[.,!?;:)]$/.test(value)){tail=value.slice(-1)+tail;value=value.slice(0,-1)}
      try{const url=new URL(/^https?:\/\//i.test(value)?value:`https://${value}`);const link=document.createElement("a");link.className="text-link";link.href=url.href;link.target="_blank";link.rel="noopener";link.textContent=value;fragment.append(link)}catch(_){fragment.append(document.createTextNode(value))}
      if(tail)fragment.append(document.createTextNode(tail)); index=match.index+match[0].length;
    }
    if(index){fragment.append(document.createTextNode(text.slice(index)));item.replaceChildren(fragment)}
  }
  function compactMessage(item){
    const container=state.ui?.messages;if(!container||!item.isConnected)return;
    const maxWidth=Math.floor(container.clientWidth*.86);if(maxWidth<1)return;
    item.style.width=`${maxWidth}px`;
    const style=getComputedStyle(item), lineHeight=parseFloat(style.lineHeight), verticalPadding=parseFloat(style.paddingTop)+parseFloat(style.paddingBottom);
    const lines=Math.max(1,Math.round((item.scrollHeight-verticalPadding)/lineHeight));
    if(lines<=1){item.style.width="fit-content";return}
    let low=Math.min(120,maxWidth),high=maxWidth;
    for(let i=0;i<8;i++){const width=(low+high)/2;item.style.width=`${width}px`;const current=Math.max(1,Math.round((item.scrollHeight-verticalPadding)/lineHeight));if(current<=lines)high=width;else low=width}
    item.style.width=`${Math.min(maxWidth,Math.ceil(high+12))}px`;
  }
  function finishMessage(item, sources, links) {
    linkifyMessage(item); compactMessage(item);
    if(sources && sources.length){ const list=document.createElement("div"); list.className="sources"; list.append("Источники:"); sources.forEach(s=>{const link=document.createElement("a");link.href=s.url;link.target="_blank";link.rel="noopener";link.textContent=`↗ ${s.question}`;list.appendChild(link)});item.appendChild(list); }
    if(links && links.length){const actions=document.createElement("div");actions.className="actions";links.forEach(action=>{try{const url=new URL(action.url,document.baseURI);if(!["http:","https:"].includes(url.protocol))return;const link=document.createElement("a");link.className="action-link";link.href=url.href;link.target="_blank";link.rel="noopener";link.textContent=action.label;actions.appendChild(link)}catch(_){}});if(actions.childElementCount)item.appendChild(actions)}
    if(!sources?.length && !links?.length){
      const style=getComputedStyle(item), oneLine=parseFloat(style.lineHeight)+parseFloat(style.paddingTop)+parseFloat(style.paddingBottom)+1;
      if(item.scrollHeight<=oneLine) item.classList.add("single-line");
    }
  }
  function renderMessage(role, text, sources) {
    const item=document.createElement("div"); item.className=`msg ${role}`; item.textContent=text;
    state.ui.messages.appendChild(item); finishMessage(item,sources,[]);
    scrollToBottom();
    return item;
  }
  function reset(){ state.messages=[]; state.sessionId=null; state.ui.messages.innerHTML=""; renderMessage("bot","Здравствуйте! Я помогу с приложением, просмотром каналов, подписками и настройками Lime HD TV."); }
  function dismissCoach(root){
    root.querySelector(".coach")?.remove(); root.querySelector(".coach-backdrop")?.remove(); root.querySelector(".fab")?.classList.remove("featured");
    try { localStorage.setItem("lime-ai-onboarding-seen-v4","1"); } catch (_) {}
  }
  function showCoach(root){
    let seen=false; try { seen=localStorage.getItem("lime-ai-onboarding-seen-v4")==="1"; } catch (_) {}
    if(state.config.onboarding===false || seen) return;
    root.querySelector(".fab").classList.add("featured");
    const backdrop=document.createElement("div"); backdrop.className="coach-backdrop";
    const coach=document.createElement("aside"); coach.className="coach"; coach.setAttribute("role","dialog"); coach.setAttribute("aria-label","Знакомство с Lime AI"); coach.innerHTML='<b>Знакомьтесь, Лайм AI</b><span>Интеллектуальный помощник, который поможет разобраться и найти нужную информацию</span><button class="coach-action">Понятно</button>';
    root.append(backdrop,coach); coach.querySelector(".coach-action").onclick=()=>dismissCoach(root); backdrop.onclick=()=>dismissCoach(root);
  }
  async function send(text){
    if(state.busy || !text.trim()) return; state.busy=true; state.ui.send.disabled=true; renderMessage("user",text);
    const typing=document.createElement("div"); typing.className="msg bot typing"; typing.innerHTML="<i></i><i></i><i></i>"; state.ui.messages.appendChild(typing);
    scrollToBottom();
    let answerItem=null, finished=false;
    try {
      const response=await fetch(`${state.config.apiUrl.replace(/\/$/,"")}/chat/stream`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,session_id:state.sessionId})});
      if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(data.detail||"Ошибка сервера")}
      if(!response.body) throw new Error("Потоковый ответ не поддерживается браузером");
      const reader=response.body.getReader(), decoder=new TextDecoder(); let buffer="";
      const handle=data=>{
        if(data.type==="meta") state.sessionId=data.session_id;
        if(data.type==="chunk"){
          typing.remove();
          if(!answerItem){answerItem=document.createElement("div");answerItem.className="msg bot";state.ui.messages.appendChild(answerItem)}
          answerItem.append(document.createTextNode(data.content||""));
          scrollToBottom();
        }
        if(data.type==="done"){
          state.sessionId=data.session_id||state.sessionId;
          if(answerItem) finishMessage(answerItem,data.sources||[],data.links||[]);
          scrollToBottom();
          finished=true;
        }
        if(data.type==="error") throw new Error(data.detail||"Ошибка сервера");
      };
      while(true){
        const {value,done}=await reader.read(); buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});
        const blocks=buffer.split("\n\n"); buffer=blocks.pop()||"";
        blocks.forEach(block=>{const line=block.split("\n").find(value=>value.startsWith("data: "));if(line) handle(JSON.parse(line.slice(6)))});
        if(done) break;
      }
      if(buffer.trim()){const line=buffer.split("\n").find(value=>value.startsWith("data: "));if(line) handle(JSON.parse(line.slice(6)))}
      if(!finished && answerItem) finishMessage(answerItem,[],[]);
    }
    catch(error){ typing.remove(); answerItem?.remove(); renderMessage("bot",`Не удалось получить ответ. ${error.message}`); }
    finally{ state.busy=false; state.ui.send.disabled=false; state.ui.input.focus(); }
  }
  function init(config){
    if(state.config) return; state.config={apiUrl:"http://localhost:8000",title:"Lime AI",...config};
    const host=document.createElement("div"), root=host.attachShadow({mode:"open"}); document.body.appendChild(host);
    root.innerHTML=`<style>${css}</style><section class="panel" id="lime-ai-panel" role="dialog" aria-label="Чат поддержки" aria-hidden="true"><header><div class="logo">${iconMarkup("logo")||"L"}</div><div class="title"><b>${esc(state.config.title)}</b><span>Поддержка Lime HD TV</span></div><button class="x" aria-label="Закрыть">${iconMarkup("close")}</button></header><main class="messages" aria-live="polite"></main><form><textarea maxlength="1000" rows="1" placeholder="Напишите вопрос…" aria-label="Сообщение"></textarea><button class="send" aria-label="Отправить">${iconMarkup("send")}</button></form><div class="note">Ответы формируются на основе базы знаний Lime HD TV</div></section><button class="fab" aria-label="Открыть чат" aria-controls="lime-ai-panel" aria-expanded="false">${iconMarkup("chat")}</button>`;
    state.ui={panel:root.querySelector(".panel"),messages:root.querySelector(".messages"),input:root.querySelector("textarea"),send:root.querySelector(".send")}; reset();
    const fab=root.querySelector(".fab");
    const toggle=()=>{const open=state.ui.panel.classList.toggle("open");state.ui.panel.setAttribute("aria-hidden",String(!open));fab.setAttribute("aria-expanded",String(open));if(open)setTimeout(()=>state.ui.input.focus(),440)};
    fab.onclick=()=>{dismissCoach(root);toggle()}; root.querySelector(".x").onclick=toggle;
    root.querySelector("form").onsubmit=e=>{e.preventDefault();const value=state.ui.input.value;state.ui.input.value="";send(value)};
    state.ui.input.onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();root.querySelector("form").requestSubmit();}};
    showCoach(root);
  }
  global.LimeAI={init};
})(window);
