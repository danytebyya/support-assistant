(function (global) {
  "use strict";
  if (global.LimeAI) return;

  const state = { config: null, messages: [], sessionId: null, busy: false, controller: null };
  const defaultIcons = {
    chat: '<svg viewBox="0 0 24 24"><path d="M20 15a3 3 0 0 1-3 3H8l-5 3V6a3 3 0 0 1 3-3h11a3 3 0 0 1 3 3z"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M21 3 3 21M3 3l18 18"/></svg>',
    edit: '<svg viewBox="0 0 24 24"><path d="M13 21h8M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>',
    send: '<svg viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4zM22 2 11 13"/></svg>'
  };



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
    const text=item.textContent, pattern=/(?:[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|https?:\/\/[^\s]+|(?:[a-z0-9-]+\.)+(?:tv|ru|com|net|org)(?:\/[^\s]*)?)/gi;
    const fragment=document.createDocumentFragment(); let index=0, match;
    while((match=pattern.exec(text))){
      fragment.append(document.createTextNode(text.slice(index,match.index)));
      let value=match[0], tail="";
      while(/[.,!?;:)]$/.test(value)){tail=value.slice(-1)+tail;value=value.slice(0,-1)}
      try{const isEmail=/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i.test(value);const url=new URL(isEmail?`mailto:${value}`:(/^https?:\/\//i.test(value)?value:`https://${value}`));const link=document.createElement("a");link.className="text-link";link.href=url.href;link.textContent=value;if(!isEmail){link.target="_blank";link.rel="noopener"}fragment.append(link)}catch(_){fragment.append(document.createTextNode(value))}
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
    if(sources && sources.length){ const list=document.createElement("div"); list.className="sources"; list.append("Источники:"); sources.forEach(s=>{try{const url=new URL(s.url,document.baseURI);if(!["http:","https:"].includes(url.protocol))return;const link=document.createElement("a");link.href=url.href;link.target="_blank";link.rel="noopener";link.textContent=`↗ ${s.question}`;list.appendChild(link)}catch(_){}});if(list.childElementCount>0)item.appendChild(list); }
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
  function reset(){
    state.controller?.abort(); state.controller=null; state.busy=false; state.messages=[]; state.sessionId=null;
    state.ui.messages.innerHTML=""; state.ui.input.value=""; state.ui.send.disabled=false; resizeInput();
    renderMessage("bot","Здравствуйте! Я помогу разобраться в работе Lime HD TV. Задайте вопрос о приложении, просмотре каналов, подписке или настройках.");
  }
  function resizeInput(){
    const input=state.ui.input;
    input.style.height="43px";
    const maxHeight=parseFloat(getComputedStyle(input).maxHeight);
    input.style.height=`${Math.min(input.scrollHeight,maxHeight)}px`;
    input.style.overflowY=input.scrollHeight>maxHeight+1?"auto":"hidden";
  }
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
    const controller=new AbortController(); state.controller=controller;
    const typing=document.createElement("div"); typing.className="msg bot typing"; typing.innerHTML="<i></i><i></i><i></i>"; state.ui.messages.appendChild(typing);
    scrollToBottom();
    let answerItem=null, finished=false;
    try {
      const response=await fetch(`${state.config.apiUrl.replace(/\/$/,"")}/chat/stream`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,session_id:state.sessionId}),signal:controller.signal});
      if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(data.detail||"Ошибка сервера")}
      if(!response.body) throw new Error("Потоковый ответ не поддерживается браузером");
      const reader=response.body.getReader(), decoder=new TextDecoder(); let buffer="";
      const handle=data=>{
        if(state.controller!==controller) return;
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
    catch(error){ if(error.name!=="AbortError"){typing.remove();answerItem?.remove();renderMessage("bot",`Не удалось получить ответ. ${error.message}`)} }
    finally{ if(state.controller===controller){state.controller=null;state.busy=false;state.ui.send.disabled=false;state.ui.input.focus()} }
  }
  function init(config){
    if(state.config) return; state.config={apiUrl:"http://localhost:8000",title:"Lime AI",...config};
    const host=document.createElement("div"), root=host.attachShadow({mode:"open"});
    host.style.cssText="position:static!important;margin:0!important;padding:0!important;border:0!important;width:0!important;height:0!important;";
    document.body.appendChild(host);
    const cssUrl=new URL("widget/widget.css", state.config.apiUrl.replace(/\/$/,"")+"/").href;
    root.innerHTML=`<style>:host{color-scheme:light;--lime:#00871e;--lime-hover:#006417;--dark:#132019;--muted:#68746d;--surface:#fff;--footer-bg:#fff;--message-bg:#f5f6f5;--input-bg:#fff;--action-bg:#e9e9e9;--action-hover:#e5e8e6;--action-text:#2e3631;--link:#3c6814;--note:#89928d;--tooltip-bg:#fff;--tooltip-text:#111;--coach-bg:#fff;--coach-title:#00871e;--coach-text:#343b37;--coach-shadow:0 20px 60px #00000073;--typing:#8b968e;--radius:1rem;--button-radius:0.75rem;--message-radius-compact:0.65rem;--border-color:#e1e3e2;--border:1px solid var(--border-color);--shadow:0 18px 55px #10281938;font:14px/1.45 Inter,system-ui,-apple-system,sans-serif;color:var(--dark)}*{box-sizing:border-box}.fab{position:fixed;right:22px;bottom:22px;width:60px;height:60px;border:0;border-radius:var(--button-radius);background:var(--lime);color:#fff;cursor:pointer;display:grid;place-items:center;opacity:1;visibility:visible;pointer-events:auto;transform:scale(1);transition:background-color .2s,opacity .16s ease,transform .24s ease;z-index:2147483647}.fab:hover{background:var(--lime-hover)}svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.fab img{width:24px;height:24px}.send img{width:19px;height:19px}.header-action img{width:16px;height:16px;filter:brightness(0) invert(1)}.header-action img,.header-action svg{transition:transform .14s ease}.header-action:active img,.header-action:active svg{transform:scale(.78)}.logo img{width:24px;height:24px}img{display:block;object-fit:contain}.panel{position:fixed;right:22px;bottom:22px;width:min(390px,calc(100vw - 24px));height:min(650px,calc(100vh - 44px));background:var(--surface);border:var(--border);border-radius:var(--radius);clip-path:inset(0 round var(--radius));isolation:isolate;box-shadow:var(--shadow);overflow:hidden;display:flex;flex-direction:column;opacity:0;visibility:hidden;pointer-events:none;transform:scale(.12);transform-origin:calc(100% - 30px) calc(100% - 30px);transition:transform .44s cubic-bezier(.22,.8,.25,1),opacity .14s ease,visibility 0s linear .44s;z-index:2147483646}.panel.open{opacity:1;visibility:visible;pointer-events:auto;transform:scale(1);transition:transform .44s cubic-bezier(.22,.8,.25,1),opacity .12s ease,visibility 0s}.panel.open ~ .fab{opacity:0;transform:scale(.72);pointer-events:none}header{background:var(--lime);color:#fff;padding:19px 20px;display:flex;align-items:center;gap:8px}.logo{width:38px;height:38px;flex:0 0 38px;margin-right:4px;background:var(--lime);color:var(--dark);display:grid;place-items:center;font-weight:900}.logo img{width:38px;height:38px;border-radius:0;object-fit:contain}.title{flex:1;display:flex;flex-direction:column;gap:1px}.title b{display:block;font-size:15px;line-height:1.15}.title span{font-size:12px;line-height:1.15;color:#fff;opacity:.82}.header-action{position:relative;width:32px;height:32px;flex:0 0 32px;border:0;color:#fff;background:transparent;cursor:pointer;padding:7px;border-radius:50%;display:grid;place-items:center;transition:background-color .18s}.header-action:hover{background:#ffffff24}.header-action svg{width:16px;height:16px}.header-action:after{content:attr(data-tooltip);position:absolute;top:calc(100% + 9px);right:0;width:max-content;max-width:130px;padding:5px 8px;border:0;border-radius:.45rem;background:var(--tooltip-bg);color:var(--tooltip-text);font:500 11px/1.25 Inter,system-ui,-apple-system,sans-serif;white-space:nowrap;box-shadow:0 4px 12px #1020182e;opacity:0;visibility:hidden;pointer-events:none;transform:translateY(-2px);transition:opacity .12s ease,transform .12s ease,visibility 0s linear .12s;z-index:2}.header-action:hover:after,.header-action:focus-visible:after{opacity:1;visibility:visible;transform:translateY(0);transition-delay:1s}header.tooltips-warm .header-action:hover:after{transition-delay:0s}.header-action:focus-visible{outline:2px solid #fff;outline-offset:2px}.messages{flex:1;overflow:auto;padding:18px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth}.msg{width:fit-content;max-width:86%;padding:11px 13px;border-radius:var(--radius);white-space:pre-wrap;overflow-wrap:anywhere;text-wrap:pretty}.msg.single-line{border-radius:var(--message-radius-compact)}.bot{align-self:flex-start;background:var(--message-bg);border:0}.user{align-self:flex-end;background:var(--lime);color:#fff}.text-link{color:var(--link);font-weight:600;text-decoration:underline;text-underline-offset:2px}.user .text-link{color:#fff}.sources{font-size:11px;margin-top:8px;padding-top:8px;border-top:var(--border)}.sources a{display:block;color:var(--link);text-decoration:none;margin-top:4px}.actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}.action-link{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:8px 12px;border-radius:var(--button-radius);background:var(--action-bg);color:var(--action-text);text-decoration:none;font-size:12px;font-weight:600;line-height:1.2;transition:background-color .18s}.action-link:only-child{width:100%}.action-link:hover{background:var(--action-hover)}.typing{display:flex;gap:5px;padding:14px}.typing i{width:6px;height:6px;border-radius:50%;background:var(--typing);animation:pulse 1s infinite}.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}@keyframes pulse{50%{opacity:.25;transform:translateY(-2px)}}form{padding:13px;background:var(--footer-bg);border-top:var(--border);display:flex;gap:9px;align-items:flex-end}textarea{font:inherit;resize:none;height:43px;min-height:43px;max-height:calc(4.35em + 24px);overflow-y:hidden;flex:1;border:var(--border);border-radius:var(--button-radius);padding:11px 12px;outline:0;background:var(--input-bg);color:var(--dark);caret-color:var(--lime)}textarea::placeholder{color:var(--muted)}textarea:focus{border-color:#888f8b}.send{width:43px;height:43px;border:0;border-radius:var(--button-radius);background:var(--lime);display:grid;place-items:center;cursor:pointer;transition:background-color .2s}.send:hover:not(:disabled){background:var(--lime-hover)}.send:disabled{opacity:.45;cursor:default}.send svg{width:19px}.note{padding:0 16px 10px;background:var(--footer-bg);color:var(--note);font-size:10px;text-align:center}.note a{color:inherit;text-decoration:underline;text-underline-offset:2px;transition:color .18s}.note a:hover{color:var(--link)}.coach{position:fixed;right:22px;bottom:96px;width:390px;padding:19px;border-radius:var(--radius);background:var(--coach-bg);color:#132019;box-shadow:var(--coach-shadow);z-index:2147483647;opacity:1}.coach:after{content:"";position:absolute;right:22px;bottom:-8px;width:16px;height:16px;background:var(--coach-bg);transform:rotate(45deg)}.coach b{display:block;margin-bottom:6px;font-size:14px;color:var(--coach-title)}.coach span{display:block;font-size:14px;line-height:1.45;color:var(--coach-text)}.coach-action{position:relative;width:100%;margin-top:14px;padding:8px 15px;border:0;border-radius:var(--button-radius);background:var(--lime);color:#fff;font:inherit;font-weight:500;cursor:pointer;transition:background-color .18s}.coach-action:hover{background:var(--lime-hover)}.coach-backdrop{position:fixed;inset:0;background:#09140c66;z-index:2147483645;opacity:1}@media (max-width:768px){.panel{position:fixed;inset:0;width:100vw;height:100dvh;max-height:none;border:0;clip-path:inset(0);transform:scale(.08);transform-origin:calc(100% - 45px) calc(100% - 45px);overscroll-behavior:contain;touch-action:none}.panel.open{transform:scale(1);border-radius:0;clip-path:inset(0)}.fab{right:max(15px,env(safe-area-inset-right));bottom:max(15px,env(safe-area-inset-bottom))}.coach{right:14px;bottom:88px;width:calc(100vw - 28px)}header{flex-shrink:0;padding-top:max(18px,env(safe-area-inset-top))}.messages{flex:1;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;touch-action:pan-y}form{flex-shrink:0;padding-bottom:max(10px,env(safe-area-inset-bottom))}textarea{font-size:16px}.note{flex-shrink:0;padding-bottom:max(8px,env(safe-area-inset-bottom))}}@media (prefers-color-scheme:dark){:host{color-scheme:dark;--dark:#f1f4f2;--muted:#929c96;--surface:#000;--footer-bg:#000;--message-bg:#15171a;--input-bg:#1d211e;--action-bg:#2a302c;--action-hover:#353c37;--action-text:#f1f4f2;--link:#7fd18a;--note:#919a94;--tooltip-bg:#272c29;--tooltip-text:#f5f7f6;--coach-bg:#181b19;--coach-title:#20b845;--coach-text:#e0e5e2;--coach-shadow:0 20px 60px #000000a6;--typing:#9aa49d;--border-color:#373d39;--shadow:0 20px 60px #00000080}.header-action:after{box-shadow:0 5px 18px #0008}.coach-backdrop{background:#03060499}}@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}</style><link rel="stylesheet" href="${esc(cssUrl)}"><section class="panel" id="lime-ai-panel" role="dialog" aria-label="Чат поддержки" aria-hidden="true"><header><div class="logo">${iconMarkup("logo")||"L"}</div><div class="title"><b>${esc(state.config.title)}</b><span>Поддержка Lime HD TV</span></div><button class="header-action new-chat" type="button" aria-label="Новый чат" data-tooltip="Новый чат">${iconMarkup("edit")}</button><button class="header-action x" type="button" aria-label="Закрыть чат" data-tooltip="Закрыть чат">${iconMarkup("close")}</button></header><main class="messages" aria-live="polite"></main><form><textarea maxlength="1000" rows="1" placeholder="Напишите вопрос…" aria-label="Сообщение"></textarea><button class="send" aria-label="Отправить">${iconMarkup("send")}</button></form><div class="note">Ответы формируются на основе базы знаний <a href="https://limehd.tv/" target="_blank" rel="noopener">Lime HD TV</a></div></section><button class="fab" aria-label="Открыть чат" aria-controls="lime-ai-panel" aria-expanded="false">${iconMarkup("chat")}</button>`;
    state.ui={panel:root.querySelector(".panel"),messages:root.querySelector(".messages"),input:root.querySelector("textarea"),send:root.querySelector(".send")}; reset();
    const fab=root.querySelector(".fab");
    const chatHeader=root.querySelector("header"), headerActions=[...root.querySelectorAll(".header-action")];
    let tooltipShowTimer, tooltipResetTimer;
    headerActions.forEach(action=>{
      action.addEventListener("mouseenter",()=>{
        clearTimeout(tooltipResetTimer);
        if(chatHeader.classList.contains("tooltips-warm")) return;
        clearTimeout(tooltipShowTimer);
        tooltipShowTimer=setTimeout(()=>chatHeader.classList.add("tooltips-warm"),1000);
      });
      action.addEventListener("mouseleave",()=>{
        clearTimeout(tooltipShowTimer);
        tooltipResetTimer=setTimeout(()=>{
          if(!headerActions.some(button=>button.matches(":hover"))) chatHeader.classList.remove("tooltips-warm");
        },160);
      });
    const updateViewport = () => {
      if (!state.ui?.panel || window.innerWidth > 768) return;
      if (window.visualViewport && state.ui.panel.classList.contains("open")) {
        const vv = window.visualViewport;
        state.ui.panel.style.height = `${vv.height}px`;
        state.ui.panel.style.top = `${vv.offsetTop}px`;
        scrollToBottom();
      }
    };
    const resetViewport = () => {
      if (!state.ui?.panel) return;
      state.ui.panel.style.height = "";
      state.ui.panel.style.top = "";
    };
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", updateViewport);
      window.visualViewport.addEventListener("scroll", updateViewport);
    }
    const toggle = () => {
      const open = state.ui.panel.classList.toggle("open");
      state.ui.panel.setAttribute("aria-hidden", String(!open));
      fab.setAttribute("aria-expanded", String(open));
      if (open) {
        if (window.innerWidth <= 768) {
          document.body.style.overflow = "hidden";
          updateViewport();
        }
        state.ui.input.focus();
      } else {
        document.body.style.overflow = "";
        resetViewport();
      }
    };
    fab.onclick = () => { dismissCoach(root); toggle(); }; root.querySelector(".x").onclick = toggle;
    root.querySelector(".new-chat").onclick = () => { reset(); state.ui.input.focus(); };
    root.querySelector("form").onsubmit = e => { e.preventDefault(); const value = state.ui.input.value; state.ui.input.value = ""; resizeInput(); send(value); };
    state.ui.input.oninput = resizeInput;
    state.ui.input.onfocus = () => { if (window.innerWidth <= 768) updateViewport(); };
    state.ui.input.onkeydown = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); root.querySelector("form").requestSubmit(); } };
    showCoach(root);
  }
  global.LimeAI={init};
})(window);
