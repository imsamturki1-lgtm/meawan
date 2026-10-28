import gradio as gr
import os
import hashlib, json, html, tempfile, re
from datetime import datetime, timezone
from gtts import gTTS

AR_URL = 'https://vocal-cocada-7ad1b3.netlify.app'

TASKS = {
 'bag': {'ar': ['افتح الحقيبة','ضع الكتاب داخل الحقيبة','أغلق الحقيبة'], 'en':['Open your bag','Put the book inside your bag','Close your bag']},
 'room': {'ar':['رتب سريرك','ضع الملابس في مكانها','رتب أغراضك','تأكد من نظافة الغرفة'], 'en':['Make your bed','Put your clothes away','Organize your belongings','Check your room']},
 'teeth': {'ar':['أحضر فرشاة الأسنان','ضع المعجون على الفرشاة','نظف أسنانك','اغسل الفرشاة'], 'en':['Get your toothbrush','Apply toothpaste','Brush your teeth','Rinse your toothbrush']}
}
TEXT = {
 'ar': {
  'title':'مِعوان', 'tagline':'مساعدك في كل خطوة نحو الاستقلالية', 'welcome':'مرحبًا بك في مِعوان', 'intro':'اختر المهمة وطريقة المساعدة المناسبة لك.',
  'task':'المهمة اليومية','profile':'طريقة المساعدة','level':'مستوى المساعدة','start':'ابدأ المهمة','next':'أنجزت الخطوة','voice':'استمع للتعليمات','audio':'التعليمات الصوتية',
  'ready':'اختر مهمة واضغط ابدأ المهمة.','done':'أحسنت! أكملت المهمة بنجاح.','step':'الخطوة','of':'من','progress':'التقدم',
  'ar_heading':'مساعد الواقع المعزز','ar_open':'فتح تجربة AR بالكاميرا','history':'لوحة متابعة الأسرة','show':'عرض الإنجازات','verify':'التحقق من سلامة السجلات',
  'records':'سجلات الإنجاز','result':'نتيجة التحقق','empty':'لا توجد إنجازات مسجلة بعد.','valid':'نجح فحص سلامة بصمات السجلات.','invalid':'تم اكتشاف خلل في سلامة السجلات.',
  'tasks':[('تجهيز الحقيبة','bag'),('ترتيب الغرفة','room'),('تنظيف الأسنان','teeth')],
  'profiles':[('إرشادات مبسطة','simple'),('إرشادات مرئية','visual'),('إرشادات نصية','text'),('أزرار كبيرة','motor')],
  'levels':[('مساعدة كاملة','high'),('مساعدة متوسطة','medium'),('مساعدة بسيطة','low')]},
 'en': {
  'title':'MEAWAN','tagline':'Your companion toward independence','welcome':'Welcome to MEAWAN','intro':'Choose your task and preferred guidance.',
  'task':'Daily Task','profile':'Guidance Preference','level':'Assistance Level','start':'Start Task','next':'Step Completed','voice':'Listen to Instructions','audio':'Voice Instructions',
  'ready':'Choose a task and press Start Task.','done':'Well done! You completed the task.','step':'Step','of':'of','progress':'Progress',
  'ar_heading':'Augmented Reality Assistant','ar_open':'Open AR Camera Experience','history':'Family Dashboard','show':'View Achievements','verify':'Verify Records',
  'records':'Achievement Records','result':'Verification Result','empty':'No achievements recorded yet.','valid':'Record hashes passed integrity verification.','invalid':'Record integrity check failed.',
  'tasks':[('Pack My Bag','bag'),('Tidy My Room','room'),('Brush My Teeth','teeth')],
  'profiles':[('Simplified Guidance','simple'),('Visual Guidance','visual'),('Text Guidance','text'),('Large Buttons','motor')],
  'levels':[('Full Assistance','high'),('Moderate Assistance','medium'),('Minimal Assistance','low')]}
}
SVG = {
 'bag': '<rect x="72" y="65" width="96" height="110" rx="18" fill="#7C3AED"/><path d="M96 65V48Q120 24 144 48V65" fill="none" stroke="#C4B5FD" stroke-width="9"/><rect x="87" y="102" width="66" height="52" rx="10" fill="#A78BFA"/>',
 'room': '<rect x="35" y="110" width="170" height="65" rx="12" fill="#2563EB"/><rect x="40" y="86" width="65" height="35" rx="9" fill="#93C5FD"/><rect x="110" y="86" width="90" height="35" rx="9" fill="#60A5FA"/>',
 'teeth': '<path d="M75 55 Q50 90 75 150 Q95 210 112 165 Q120 145 128 165 Q146 210 165 150 Q190 90 165 55 Q143 38 120 55 Q97 38 75 55Z" fill="#E2E8F0" stroke="#7C3AED" stroke-width="7"/>'
}

# Demo-only hash-linked local ledger. It is NOT a decentralized blockchain.
blockchain = []
received_ar_ids = set()
def calculate_hash(block):
    payload = json.dumps(block, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def add_block(task_id, level, source):
    record = {'index':len(blockchain)+1, 'task':task_id, 'status':'Completed', 'assistance_level':level,
              'source':source, 'timestamp':datetime.now(timezone.utc).isoformat(),
              'previous_hash':blockchain[-1]['hash'] if blockchain else '0'}
    record['hash'] = calculate_hash(record)
    blockchain.append(record)

def verify_blockchain():
    for i, block in enumerate(blockchain):
        fields = {k:v for k,v in block.items() if k != 'hash'}
        expected = blockchain[i-1]['hash'] if i else '0'
        if block.get('hash') != calculate_hash(fields) or block.get('previous_hash') != expected or block.get('index') != i+1:
            return False
    return True

css = '''
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&family=Inter:wght@400;500;700&display=swap');
body, .gradio-container {background:#0F172A!important;color:white!important;min-height:100vh;}
.gradio-container {max-width:850px!important;margin:auto!important;}
.gradio-container, .gradio-container * {font-family:'Tajawal','Inter',sans-serif!important;}
.gradio-container label,.gradio-container .prose,.gradio-container .prose h3 {color:white!important;}
.meawan-card {background:#1E293B;border:1px solid #334155;border-radius:18px;padding:24px;margin:14px 0;color:white;}
.meawan-card h1,.meawan-card h2,.meawan-card p {color:white!important;}
.meawan-card p {color:#CBD5E1!important;}
.meawan-header {text-align:center;}
.meawan-header h1 {font-size:42px;font-weight:800;margin:0;}
.step-card {text-align:center;}
.step-card h2 {font-size:28px;line-height:1.5;}
.progress-track {height:12px;border-radius:20px;overflow:hidden;background:#334155;margin-top:12px;}
.progress-fill {height:100%;background:#16A085;border-radius:20px;}
.primary-btn {background:#2563EB!important;color:white!important;border:0!important;border-radius:12px!important;min-height:56px!important;}
.next-btn,.verify-btn {background:#16A085!important;color:white!important;border:0!important;border-radius:12px!important;min-height:54px!important;}
.voice-btn {background:#7C3AED!important;color:white!important;border:0!important;border-radius:12px!important;min-height:54px!important;}
.ar-button {display:block;text-align:center;background:#7C3AED;color:white!important;padding:17px;border-radius:12px;text-decoration:none!important;font-weight:700;font-size:18px;}
.ar-button:focus {outline:3px solid #F59E0B;}
'''

def header(lang):
    t = TEXT[lang]; direction = 'rtl' if lang=='ar' else 'ltr'
    return f'<div class="meawan-card meawan-header" dir="{direction}"><h1>{t["title"]}</h1><p>{t["tagline"]}</p></div>'

def welcome(lang):
    t = TEXT[lang]; direction = 'rtl' if lang=='ar' else 'ltr'
    return f'<div class="meawan-card" dir="{direction}"><h2>{t["welcome"]}</h2><p>{t["intro"]}</p></div>'

def ar_link(lang):
    t=TEXT[lang]
    return f'<div class="meawan-card" dir="{"rtl" if lang=="ar" else "ltr"}"><h2>{t["ar_heading"]}</h2><a class="ar-button" href="{AR_URL}" target="_blank" rel="noopener noreferrer">{t["ar_open"]}</a></div>'

def display_step(lang, task_id, index, active, level, profile):
    t=TEXT[lang]; direction='rtl' if lang=='ar' else 'ltr'
    if not active:
        return f'<div class="meawan-card step-card" dir="{direction}"><p>{t["ready"]}</p></div>'
    steps=TASKS[task_id][lang]; total=len(steps); index=min(index,total)
    if index==total:
        return f'<div class="meawan-card step-card" dir="{direction}"><h2 style="color:#5EEAD4!important">{t["done"]}</h2><p>100%</p><div class="progress-track"><div class="progress-fill" style="width:100%"></div></div></div>'
    step_label=f'{t["step"]} {index+1} {t["of"]} {total}' if level!='low' else f'{index+1}/{total}'
    art=f'<svg viewBox="0 0 240 230" width="180" height="180" role="img" aria-label="{html.escape(steps[index])}">{SVG[task_id]}</svg>' if profile in ('simple','visual','motor') else ''
    pct=round(index*100/total)
    size='36px' if profile=='motor' else '28px'
    return f'<div class="meawan-card step-card" dir="{direction}"><p>{step_label}</p>{art}<h2 style="font-size:{size}">{html.escape(steps[index])}</h2><p>{t["progress"]}: {pct}%</p><div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div></div>'

def start_task(lang, task_id, level, profile):
    state=(task_id,0,True,level)
    return state, display_step(lang,task_id,0,True,level,profile),gr.update(visible=True),gr.update(visible=True),gr.update(value=None,visible=False)

def next_step(lang, profile, state):
    task_id,index,active,level=state
    if not active:
        return state,display_step(lang,task_id,0,False,level,profile),gr.update(visible=False),gr.update(visible=False),gr.update(value=None,visible=False)
    total=len(TASKS[task_id][lang]); new_index=min(index+1,total)
    if index<total and new_index==total:
        add_block(task_id,level,'App')
    finished=new_index==total
    new_state=(task_id,new_index,True,level)
    return new_state,display_step(lang,task_id,new_index,True,level,profile),gr.update(visible=not finished),gr.update(visible=not finished),gr.update(value=None,visible=False)

def reset_task(lang,task_id,level,profile):
    return (task_id,0,False,level),display_step(lang,task_id,0,False,level,profile),gr.update(visible=False),gr.update(visible=False),gr.update(value=None,visible=False)

def refresh_step(lang,level,profile,state):
    task_id,index,active,saved_level=state
    return display_step(lang,task_id,index,active,saved_level if active else level,profile)

def change_language(lang,state,task_id,level,profile):
    t=TEXT[lang]; active_task,index,active,saved_level=state
    shown=active_task if active else task_id
    visible=active and index<len(TASKS[shown][lang])
    return (header(lang),welcome(lang),ar_link(lang),
            gr.update(choices=t['tasks'],label=t['task'],value=task_id),
            gr.update(choices=t['profiles'],label=t['profile'],value=profile),
            gr.update(choices=t['levels'],label=t['level'],value=level),
            gr.update(value=t['start']),gr.update(value=t['next'],visible=visible),
            gr.update(value=t['voice'],visible=visible),
            display_step(lang,shown,index,active,saved_level if active else level,profile),
            gr.update(value=None,visible=False,label=t['audio']),
            gr.update(value=f'### {t["history"]}'),gr.update(value=t['show']),gr.update(value=t['verify']),
            gr.update(label=t['records'],value=show_history(lang)),gr.update(label=t['result'],value=''))

def speak_instruction(lang,state):
    task_id,index,active,_=state
    if not active or index>=len(TASKS[task_id][lang]):
        return gr.update(value=None,visible=False)
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp3',delete=False) as f:
            filename=f.name
        gTTS(text=TASKS[task_id][lang][index],lang=lang,slow=False).save(filename)
        return gr.update(value=filename,visible=True)
    except Exception:
        gr.Warning('تعذر إنشاء الصوت / Could not generate audio')
        return gr.update(value=None,visible=False)

def show_history(lang):
    t=TEXT[lang]
    if not blockchain: return t['empty']
    names=dict((value,label) for label,value in t['tasks'])
    levels=dict((value,label) for label,value in t['levels'])
    items=[]
    for b in reversed(blockchain):
        if lang=='ar':
            items.append(f'المهمة: {names.get(b["task"],b["task"])}\nالحالة: مكتملة\nالمصدر: {b["source"]}\nمستوى المساعدة: {levels.get(b["assistance_level"],b["assistance_level"])}\nالوقت: {b["timestamp"]}\nHash: {b["hash"][:24]}...')
        else:
            items.append(f'Task: {names.get(b["task"],b["task"])}\nStatus: Completed\nSource: {b["source"]}\nAssistance: {levels.get(b["assistance_level"],b["assistance_level"])}\nTime: {b["timestamp"]}\nHash: {b["hash"][:24]}...')
    return '\n\n--------------------\n\n'.join(items)

def check_records(lang):
    return TEXT[lang]['valid'] if verify_blockchain() else TEXT[lang]['invalid']

def receive_ar_completion(lang, request:gr.Request):
    params=dict(request.query_params) if request else {}
    task_id=params.get('ar_done','')
    completion_id=params.get('completion_id','')
    if task_id=='bag' and re.fullmatch(r'[0-9a-f]{32}',completion_id):
        if completion_id not in received_ar_ids:
            add_block('bag','high','AR')
            received_ar_ids.add(completion_id)
            message='تم تسجيل إنجاز AR في السجل التجريبي.' if lang=='ar' else 'AR completion was recorded in the demo ledger.'
        else:
            message='تم تسجيل هذا الإنجاز سابقًا.' if lang=='ar' else 'This completion was already recorded.'
    else:
        message='مرحبًا بك في مِعوان.' if lang=='ar' else 'Welcome to MEAWAN.'
    return f'<div class="meawan-card" dir="{"rtl" if lang=="ar" else "ltr"}"><p>{message}</p></div>',show_history(lang),check_records(lang)

with gr.Blocks(title='MEAWAN | مِعوان',css=css,theme=gr.themes.Base(primary_hue='blue',neutral_hue='slate')) as demo:
    state=gr.State(('bag',0,False,'high'))
    language=gr.Radio(choices=[('العربية','ar'),('English','en')],value='ar',label='Language / اللغة')
    title_html=gr.HTML(header('ar'))
    ar_status=gr.HTML('<div class="meawan-card">مرحبًا بك في مِعوان.</div>')
    welcome_html=gr.HTML(welcome('ar'))
    task=gr.Dropdown(choices=TEXT['ar']['tasks'],value='bag',label=TEXT['ar']['task'])
    profile=gr.Dropdown(choices=TEXT['ar']['profiles'],value='simple',label=TEXT['ar']['profile'])
    level=gr.Radio(choices=TEXT['ar']['levels'],value='high',label=TEXT['ar']['level'])
    start_btn=gr.Button(TEXT['ar']['start'],elem_classes='primary-btn')
    ar_html=gr.HTML(ar_link('ar'))
    step_display=gr.HTML(display_step('ar','bag',0,False,'high','simple'))
    with gr.Row():
        voice_btn=gr.Button(TEXT['ar']['voice'],elem_classes='voice-btn',visible=False)
        next_btn=gr.Button(TEXT['ar']['next'],elem_classes='next-btn',visible=False)
    audio_player=gr.Audio(label=TEXT['ar']['audio'],type='filepath',interactive=False,autoplay=False,visible=False)
    history_heading=gr.Markdown('### '+TEXT['ar']['history'])
    history_btn=gr.Button(TEXT['ar']['show'])
    history_output=gr.Textbox(label=TEXT['ar']['records'],lines=9,interactive=False)
    verify_btn=gr.Button(TEXT['ar']['verify'],elem_classes='verify-btn')
    verify_output=gr.Textbox(label=TEXT['ar']['result'],interactive=False)

    language.change(change_language,[language,state,task,level,profile],
        [title_html,welcome_html,ar_html,task,profile,level,start_btn,next_btn,voice_btn,step_display,audio_player,history_heading,history_btn,verify_btn,history_output,verify_output])
    start_btn.click(start_task,[language,task,level,profile],[state,step_display,next_btn,voice_btn,audio_player])
    next_btn.click(next_step,[language,profile,state],[state,step_display,next_btn,voice_btn,audio_player])
    voice_btn.click(speak_instruction,[language,state],audio_player)
    task.change(reset_task,[language,task,level,profile],[state,step_display,next_btn,voice_btn,audio_player])
    profile.change(refresh_step,[language,level,profile,state],step_display)
    level.change(refresh_step,[language,level,profile,state],step_display)
    history_btn.click(show_history,language,history_output)
    verify_btn.click(check_records,language,verify_output)
    demo.load(receive_ar_completion,inputs=[language],outputs=[ar_status,history_output,verify_output],queue=False)

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")), share=False)
