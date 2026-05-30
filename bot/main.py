import os
import logging
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise RuntimeError("Falta la variable de entorno TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

states = {}
data   = {}

def uid(m):
    return m.chat.id if hasattr(m, 'chat') else m.message.chat.id

def get_state(u): return states.get(u)
def set_state(u, s): states[u] = s
def get_data(u): return data.get(u, {})
def set_val(u, k, v): data.setdefault(u, {})[k] = v
def clear(u):
    states.pop(u, None)
    data.pop(u, None)

def kb_si_no(p):
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("Si", callback_data=f"{p}_si"),
          InlineKeyboardButton("No", callback_data=f"{p}_no"))
    return m

def kb_estado():
    m = InlineKeyboardMarkup()
    for label, val in [
        ("A reciclar (0.80)",       "est_0.80"),
        ("Standard (1.00)",          "est_1.00"),
        ("Buena sin clim. (1.075)", "est_1.075"),
        ("Buena con clim. (1.175)", "est_1.175"),
        ("Muy buena (1.275)",        "est_1.275"),
        ("Reciclado 100% (1.10)",    "est_1.10"),
    ]:
        m.add(InlineKeyboardButton(label, callback_data=val))
    return m

def kb_ub():
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("0.90 inferior",      callback_data="ub_0.90"),
          InlineKeyboardButton("0.95 lev. inferior", callback_data="ub_0.95"))
    m.row(InlineKeyboardButton("1.00 similar",       callback_data="ub_1.00"),
          InlineKeyboardButton("1.05 lev. superior", callback_data="ub_1.05"))
    m.row(InlineKeyboardButton("1.10 superior",      callback_data="ub_1.10"),
          InlineKeyboardButton("1.15 muy superior",  callback_data="ub_1.15"))
    return m

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    bot.reply_to(msg,
        "Bot ACM Inmobiliario\n\n"
        "Comandos:\n"
        "/nuevo_acm - Iniciar analisis\n"
        "/generar - Generar el Excel\n"
        "/cancelar - Cancelar\n"
        "/ayuda - Instrucciones")

@bot.message_handler(commands=['ayuda'])
def cmd_ayuda(msg):
    bot.reply_to(msg,
        "Instrucciones:\n\n"
        "1) /nuevo_acm - cargas los datos del tasado\n"
        "2) Pegas los links de los comparables\n"
        "3) /generar - recibes el Excel ACM\n\n"
        "Portales: Zonaprop, Argenprop, MercadoLibre")

@bot.message_handler(commands=['nuevo_acm'])
def cmd_nuevo(msg):
    u = uid(msg)
    clear(u)
    set_state(u, 'DIR')
    bot.reply_to(msg,
        "Nuevo ACM - 1/8\n\n"
        "Direccion completa de la propiedad del cliente?\n"
        "Ej: Lavalle 1566 Piso 1 Dpto B, CABA")

@bot.message_handler(commands=['cancelar'])
def cmd_cancelar(msg):
    clear(uid(msg))
    bot.reply_to(msg, "Cancelado. Envia /nuevo_acm para empezar de nuevo.")

@bot.message_handler(commands=['generar'])
def cmd_generar(msg):
    u = uid(msg)
    if get_state(u) != 'LINKS':
        bot.reply_to(msg, "Primero inicia un ACM con /nuevo_acm")
        return
    d = get_data(u)
    links = d.get('links', [])
    if not links:
        bot.reply_to(msg, "No hay links cargados. Pega al menos uno.")
        return

    st = bot.reply_to(msg, f"Procesando {len(links)} comparable{'s' if len(links)!=1 else ''}...")

    from scraper import scrape_link
    from excel_gen import generar_excel

    comparables = []
    for i, link in enumerate(links):
        try:
            bot.edit_message_text(
                f"Analizando {i+1}/{len(links)}...\n{link[:55]}",
                msg.chat.id, st.message_id)
            comp = scrape_link(link)
            if comp:
                comparables.append(comp)
        except Exception as e:
            logger.error(f"Error scraping: {e}")

    if not comparables:
        bot.edit_message_text(
            "No pude extraer datos. Verifica que los links sean avisos individuales.",
            msg.chat.id, st.message_id)
        return

    bot.edit_message_text(
        f"Generando Excel con {len(comparables)} comparables...",
        msg.chat.id, st.message_id)

    try:
        path = generar_excel(d, comparables)
        nombre = f"ACM_{d.get('direccion','')[:20].replace(' ','_')}.xlsx"
        bot.delete_message(msg.chat.id, st.message_id)
        with open(path, 'rb') as f:
            bot.send_document(
                msg.chat.id, f,
                visible_file_name=nombre,
                caption=(
                    f"ACM listo!\n"
                    f"Direccion: {d.get('direccion','')}\n"
                    f"{len(comparables)} comparables procesados\n"
                    "Abri en Excel para ver los valores calculados."))
        import os as _os; _os.remove(path)
        clear(u)
    except Exception as e:
        logger.error(e)
        bot.edit_message_text(f"Error generando Excel: {e}", msg.chat.id, st.message_id)

@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    u = uid(msg)
    state = get_state(u)
    text = (msg.text or '').strip()

    if state == 'DIR':
        set_val(u, 'direccion', text)
        set_state(u, 'PISO')
        bot.reply_to(msg, "2/8 - Piso\n\nEn que piso esta? (0 = Planta Baja)")

    elif state == 'PISO':
        try:
            set_val(u, 'piso', int(text))
            set_state(u, 'ASC')
            bot.reply_to(msg, "3/8 - Ascensor\n\nEl edificio tiene ascensor?",
                         reply_markup=kb_si_no("asc"))
        except ValueError:
            bot.reply_to(msg, "Solo el numero. Ej: 1")

    elif state == 'ANTIG':
        try:
            set_val(u, 'antiguedad', int(text))
            set_state(u, 'ESTADO')
            bot.reply_to(msg, "5/8 - Estado constructivo:", reply_markup=kb_estado())
        except ValueError:
            bot.reply_to(msg, "Solo el numero. Ej: 30")

    elif state == 'SCUB':
        try:
            set_val(u, 'sup_cub', float(text.replace(',', '.')))
            set_state(u, 'SSEMI')
            bot.reply_to(msg, "Superficie semi cubierta (m2) - escribe 0 si no tiene:")
        except ValueError:
            bot.reply_to(msg, "Solo el numero. Ej: 41.08")

    elif state == 'SSEMI':
        try:
            set_val(u, 'sup_semi', float(text.replace(',', '.')))
        except ValueError:
            set_val(u, 'sup_semi', 0)
        set_state(u, 'SDESC')
        bot.reply_to(msg, "Superficie descubierta/patio (m2) - escribe 0 si no tiene:")

    elif state == 'SDESC':
        try:
            set_val(u, 'sup_desc', float(text.replace(',', '.')))
        except ValueError:
            set_val(u, 'sup_desc', 0)
        set_state(u, 'COCH')
        bot.reply_to(msg, "7/8 - Cochera\n\nTiene cochera?", reply_markup=kb_si_no("coch"))

    elif state == 'COCHVAL':
        try:
            set_val(u, 'cochera', float(text.replace(',', '.')))
        except ValueError:
            set_val(u, 'cochera', 0)
        set_state(u, 'DIAS')
        bot.reply_to(msg, "8/8 - Dias en el mercado (0 si no esta publicada):")

    elif state == 'DIAS':
        try:
            set_val(u, 'dias', int(text))
        except ValueError:
            set_val(u, 'dias', 0)
        set_state(u, 'UB')
        bot.reply_to(msg, "Coeficiente de Ubicacion (Ub.)\nComparando el barrio del tasado con los comparables:",
                     reply_markup=kb_ub())

    elif state == 'LINKS':
        nuevos = [l.strip() for l in text.split('\n') if l.strip().startswith('http')]
        data.setdefault(u, {}).setdefault('links', []).extend(nuevos)
        n = len(get_data(u).get('links', []))
        bot.reply_to(msg,
            f"{n} link{'s' if n!=1 else ''} cargado{'s' if n!=1 else ''}.\n"
            "Podes agregar mas o envia /generar")

@bot.callback_query_handler(func=lambda c: c.data.startswith('asc_'))
def cb_asc(call):
    u = call.message.chat.id
    set_val(u, 'ascensor', call.data.endswith('_si'))
    label = "Con ascensor" if get_data(u)['ascensor'] else "Sin ascensor"
    bot.edit_message_text(
        f"{label}\n\n4/8 - Antiguedad\n\nCuantos anos de antiguedad tiene?",
        u, call.message.message_id)
    set_state(u, 'ANTIG')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('est_'))
def cb_estado(call):
    u = call.message.chat.id
    val_str = call.data.split('_', 1)[1]
    set_val(u, 'estado_coef', float(val_str))
    from coefs import ESTADO_LABELS
    label = ESTADO_LABELS.get(val_str, val_str)
    set_val(u, 'estado_label', label)
    bot.edit_message_text(
        f"Estado: {label}\n\n6/8 - Superficie cubierta (m2)\nEj: 41.08",
        u, call.message.message_id)
    set_state(u, 'SCUB')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('coch_'))
def cb_coch(call):
    u = call.message.chat.id
    if call.data.endswith('_si'):
        bot.edit_message_text("Valor de la cochera en USD?", u, call.message.message_id)
        set_state(u, 'COCHVAL')
    else:
        set_val(u, 'cochera', 0)
        bot.edit_message_text(
            "8/8 - Dias en el mercado (0 si no esta publicada):",
            u, call.message.message_id)
        set_state(u, 'DIAS')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('ub_'))
def cb_ub(call):
    u = call.message.chat.id
    ub = float(call.data.split('_')[1])
    set_val(u, 'ub_coef', ub)
    d = get_data(u)
    from coefs import calc_sup_homolog, calc_piso_coef, calc_sup_coef, calc_dias_coef, calc_coef_total
    sup_h = calc_sup_homolog(d.get('sup_cub',0), d.get('sup_semi',0), d.get('sup_desc',0))
    pc = calc_piso_coef(d.get('piso',0), d.get('ascensor',True))
    sc = calc_sup_coef(d.get('sup_cub',0))
    dc = calc_dias_coef(d.get('dias',0))
    ct = calc_coef_total(ub, pc, 1.0, sc, d.get('estado_coef',1.0), d.get('estado_coef',1.0), dc)
    bot.edit_message_text(
        f"Datos del tasado cargados!\n\n"
        f"Direccion: {d.get('direccion','')}\n"
        f"Piso {d.get('piso',0)} | {'Con' if d.get('ascensor') else 'Sin'} ascensor\n"
        f"Cub: {d.get('sup_cub',0)}m2 | Semi: {d.get('sup_semi',0)}m2 | Desc: {d.get('sup_desc',0)}m2\n"
        f"Homolog: {sup_h} m2\n"
        f"{d.get('antiguedad','?')} anos | {d.get('dias',0)} dias\n"
        f"Estado: {d.get('estado_label','')}\n"
        f"Coef estimado: {ct}\n\n"
        "Pega los links de los comparables (uno por linea).\n"
        "Cuando termines envia /generar",
        u, call.message.message_id)
    set_state(u, 'LINKS')
    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    logger.info("Bot ACM iniciado")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
