#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Серверная версия бота ланчей (Beget, cron). Без зависимостей (urllib).
Токен: env TELEGRAM_LAUNCH_BOT_TOKEN или файл token.txt рядом со скриптом.
Файлы рядом: gantt_config.json, gantt_data.json, gantt_bot_state.json.
--post : по каждой новинке (с непустым tg) шлёт в её группу ОДИН список активных задач с кнопками «Выполнено».
--poll : ловит нажатия (getUpdates), отмечает этап done, двигает дальше, обновляет сообщение.
"""
import json, os, sys, urllib.request, urllib.error, datetime

BASE=os.path.dirname(os.path.abspath(__file__))
CONFIG=os.path.join(BASE,"gantt_config.json")
DATAF=os.path.expanduser("~/primeh1e.beget.tech/public_html/data/gantt_data.json")
STATEF=os.path.join(BASE,"gantt_bot_state.json")
TOKENF=os.path.join(BASE,"token.txt")
SOON=3

def token():
    t=os.environ.get("TELEGRAM_LAUNCH_BOT_TOKEN")
    if t: return t.strip()
    if os.path.exists(TOKENF): return open(TOKENF,encoding="utf-8").read().strip()
    raise SystemExit("no token")
TG=token()

def today(): return datetime.date.today()
def di(s): return datetime.date.fromisoformat(s)

def api(method, params):
    url="https://api.telegram.org/bot%s/%s"%(TG,method)
    data=json.dumps(params).encode()
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e: return {"ok":False,"error":e.read().decode()[:200]}
    except Exception as e: return {"ok":False,"error":str(e)}

def load():
    return json.load(open(CONFIG,encoding="utf-8")), json.load(open(DATAF,encoding="utf-8"))
def load_state():
    if os.path.exists(STATEF):
        try: return json.load(open(STATEF,encoding="utf-8"))
        except: pass
    return {"offset":0,"posts":{}}
def save_state(st): open(STATEF,"w",encoding="utf-8").write(json.dumps(st,ensure_ascii=False,indent=2))
def save_data(dat): open(DATAF,"w",encoding="utf-8").write(json.dumps(dat,ensure_ascii=False,indent=2))

def sched(p,stages):
    ov=p.get("ov",{}) or {}; d0=di(p["day0"]); res={}
    for s in stages:
        o=ov.get(str(s["id"]),{}) or {}
        st=int(o.get("start",s["start"])); dur=int(o.get("dur",s["dur"]))
        res[s["id"]]={"start":d0+datetime.timedelta(days=st),"end":d0+datetime.timedelta(days=st+dur),
                      "status":o.get("status","pending"),"resp":o.get("resp",s["resp"])}
    return res

def active(p,stages):
    t=today(); sch=sched(p,stages); out=[]
    for s in stages:
        v=sch[s["id"]]
        if v["status"]=="done": continue
        if v["status"]=="in_progress" or (v["start"]-t).days<=SOON: out.append((s,v))
    out.sort(key=lambda x:sched(p,stages)[x[0]["id"]]["start"])
    return out

def progress(p,stages):
    sch=sched(p,stages); d=sum(1 for s in stages if sch[s["id"]]["status"]=="done")
    return round(d/len(stages)*100)

def kb(pid,items):
    rows=[]
    for s,v in items:
        nm=s["name"]; nm=nm[:40]+"…" if len(nm)>42 else nm
        rows.append([{"text":"✅ %d. %s"%(s["id"],nm),"callback_data":"d:%s:%d"%(pid,s["id"])}])
    return {"inline_keyboard":rows}

def list_text(p,items,stages):
    t=today().strftime("%d.%m.%Y")
    L=["🚀 <b>Ланч: %s</b>"%p["name"]+(" (арт. %s)"%p["art"] if p.get("art") else ""),
       "<i>Активные задачи на %s · прогресс %d%%</i>"%(t,progress(p,stages)),""]
    for s,v in items:
        when=v["end"].strftime("%d.%m"); over=" ⚠️ просрочено" if v["end"]<today() else ""
        L.append("• %d. %s — %s — до %s%s"%(s["id"],s["name"],v["resp"],when,over))
    L.append(""); L.append("Нажми кнопку, когда задача выполнена 👇")
    return "\n".join(L)

def _dedup(ps):
    best={}
    for p in ps:
        c=p.get("tg")
        if not c: continue
        ov=p.get("ov",{}) or {}
        sc=sum(1 for v in ov.values() if v.get("status")=="done")
        if c not in best or sc>best[c][0]: best[c]=(sc,p)
    return [v[1] for v in best.values()]

def post():
    cfg,dat=load(); stages=cfg["stages"]; st=load_state(); st.setdefault("posts",{}); n=0
    for p in _dedup(dat.get("products",[])):
        chat=p.get("tg")
        if p.get("id")=="demo-lamp" or (p.get("name","").lower().find("пример")>=0): print("  %s: пример — пропуск"%p["name"]); continue
        if not chat: print("  %s: нет tg — пропуск"%p["name"]); continue
        items=active(p,stages)
        if not items: print("  %s: активных нет"%p["name"]); continue
        r=api("sendMessage",{"chat_id":chat,"text":list_text(p,items,stages),"parse_mode":"HTML",
              "disable_web_page_preview":True,"reply_markup":kb(p["id"],items)})
        if r.get("ok"): st["posts"][p["id"]]={"chat":chat,"mid":r["result"]["message_id"]}; n+=1; print("  %s: ok"%p["name"])
        else: print("  %s: ERR %s"%(p["name"],r.get("error")))
    save_state(st); print("постов:",n)

def refresh(p,stages,st):
    pi=st["posts"].get(p["id"]);
    if not pi: return
    items=active(p,stages)
    txt=list_text(p,items,stages) if items else "✅ <b>%s</b>: все активные задачи закрыты."%p["name"]
    api("editMessageText",{"chat_id":pi["chat"],"message_id":pi["mid"],"text":txt,"parse_mode":"HTML",
        "disable_web_page_preview":True,"reply_markup":kb(p["id"],items) if items else {"inline_keyboard":[]}})

def poll():
    cfg,dat=load(); stages=cfg["stages"]; smap={s["id"]:s for s in stages}
    st=load_state(); r=api("getUpdates",{"offset":st.get("offset",0)+1,"timeout":0})
    if not r.get("ok"): print("getUpdates ERR",r.get("error")); return
    changed=False
    for u in r.get("result",[]):
        st["offset"]=u["update_id"]; cq=u.get("callback_query")
        if not cq: continue
        data=cq.get("data","")
        if not data.startswith("d:"): continue
        try: _,pid,sid=data.split(":"); sid=int(sid)
        except: continue
        p=next((x for x in dat.get("products",[]) if x["id"]==pid),None)
        if not p:
            api("answerCallbackQuery",{"callback_query_id":cq["id"],"text":"Этот ланч удалён"})
            try:
                mm=cq["message"]
                api("editMessageText",{"chat_id":mm["chat"]["id"],"message_id":mm["message_id"],"text":"\u26a0\ufe0f Этот ланч удалён/устарел. Актуальный — в закрепе.","reply_markup":{"inline_keyboard":[]}})
            except Exception: pass
            continue
        ov=p.setdefault("ov",{}); ov.setdefault(str(sid),{})["status"]="done"; ov[str(sid)]["done"]=today().isoformat()
        sch=sched(p,stages); nxt=sorted([s for s in stages if sch[s["id"]]["status"]=="pending"],key=lambda s:sch[s["id"]]["start"])
        if nxt: p["ov"].setdefault(str(nxt[0]["id"]),{})["status"]="in_progress"
        who=cq.get("from",{}).get("first_name","")
        api("answerCallbackQuery",{"callback_query_id":cq["id"],"text":"Отмечено ✅"})
        api("sendMessage",{"chat_id":cq["message"]["chat"]["id"],
            "text":"✅ «%s» выполнено (%s). Прогресс %d%%."%(smap[sid]["name"],who,progress(p,stages)),"parse_mode":"HTML"})
        refresh(p,stages,st); changed=True; print("done",pid,sid,who)
    save_state(st)
    if changed: save_data(dat); print("данные обновлены")
    else: print("нажатий нет")

if __name__=="__main__":
    if "--post" in sys.argv: post()
    elif "--poll" in sys.argv: poll()
    else: print("--post | --poll")


def refresh_all():
    cfg,dat=load(); stages=cfg["stages"]; st=load_state(); st.setdefault("posts",{}); ch=False
    for p in _dedup(dat.get("products",[])):
        pid=p["id"]; chat=p.get("tg")
        if not chat: continue
        items=active(p,stages)
        txt=list_text(p,items,stages) if items else "✅ <b>%s</b>: все активные задачи закрыты."%p["name"]
        mk=kb(pid,items) if items else {"inline_keyboard":[]}
        pi=st["posts"].get(pid)
        if pi:
            r=api("editMessageText",{"chat_id":pi["chat"],"message_id":pi["mid"],"text":txt,"parse_mode":"HTML","disable_web_page_preview":True,"reply_markup":mk})
            if (not r.get("ok")) and ("not found" in str(r.get("error",""))):
                r2=api("sendMessage",{"chat_id":chat,"text":txt,"parse_mode":"HTML","disable_web_page_preview":True,"reply_markup":mk})
                if r2.get("ok"): st["posts"][pid]={"chat":chat,"mid":r2["result"]["message_id"]}; ch=True
        else:
            r2=api("sendMessage",{"chat_id":chat,"text":txt,"parse_mode":"HTML","disable_web_page_preview":True,"reply_markup":mk})
            if r2.get("ok"): st["posts"][pid]={"chat":chat,"mid":r2["result"]["message_id"]}; ch=True
    if ch: save_state(st)
    print("refresh done")

if "--refresh" in sys.argv:
    refresh_all()
