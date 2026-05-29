import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler, filters, ContextTypes
)

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DIR,PISO,ASC,ANTIG,ESTADO,SCUB,SSEMI,SDESC,COCH,COCHVAL,DIAS,UB,LINKS = range(13)

def kb_si_no(p):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sí", callback_data=f"{p}_si"),
        InlineKeyboardButton("❌ No", callback_data=f"{p}_no"),
    ]])

def kb_estado():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 A reciclar (0.80)",        callback_data="est_0.80")],
        [InlineKeyboardButton("⚪ Standard (1.00)",           callback_data="est_1.00")],
        [InlineKeyboardButton("🟡 Buena sin clim. (1.075)",  callback_data="est_1.075")],
        [InlineKeyboardButton("🟢 Buena con clim. (1.175)",  callback_data="est_1.175")],
        [InlineKeyboardButton("🔵 Muy buena (1.275)",         callback_data="est_1.275")],
        [InlineKeyboardButton("✨ Reciclado 100% (1.10)",     callback_data="est_1.10")],
    ])

def kb_ub():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("0.90 — inferior",       callback_data="ub_0.90"),
         InlineKeyboardButton("0.95 — lev. inferior",  callback_data="ub_0.95")],
        [InlineKeyboardButton("1.00 — similar",        callback_data="ub_1.00"),
         InlineKeyboardButton("1.05 — lev. superior",  callback_data="ub_1.05")],
        [InlineKeyboardButton("1.10 — superior",       callback_data="ub_1.10"),
         InlineKeyboardButton("1.15 — muy superior",   callback_data="ub_1.15")],
    ])

async def start(u: Update, _):
    await u.message.reply_text(
        "🏠 *Bot ACM Inmobiliario*\n\n"
        "Comandos:\n"
        "• /nuevo\\_acm — Iniciar análisis\n"
        "• /generar — Generar el Excel\n"
        "• /cancelar — Cancelar\n"
        "• /ayuda — Instrucciones",
        parse_mode="Markdown")

async def ayuda(u: Update, _):
    await u.message.reply_text(
        "📖 *Instrucciones*\n\n"
        "1️⃣ /nuevo\\_acm → cargás los datos del tasado\n"
        "2️⃣ Pegás los links de los comparables (uno por línea)\n"
        "3️⃣ /generar → recibís el Excel ACM completo\n\n"
        "Portales compatibles: Zonaprop · Argenprop · MercadoLibre",
        parse_mode="Markdown")

async def nuevo_acm(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await u.message.reply_text(
        "🏠 *Nuevo ACM — 1/8*\n\n"
        "¿Dirección completa de la propiedad del cliente?\n"
        "_Ej: Lavalle 1566 Piso 1° Dpto B, CABA_",
        parse_mode="Markdown")
    return DIR

async def get_dir(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["direccion"] = u.message.text.strip()
    await u.message.reply_text(
        "📍 *2/8 — Piso*\n\n¿En qué piso está? _(0 = Planta Baja)_",
        parse_mode="Markdown")
    return PISO

async def get_piso(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["piso"] = int(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ Solo el número. Ej: *1*", parse_mode="Markdown")
        return PISO
    await u.message.reply_text(
        "🛗 *3/8 — Ascensor*\n\n¿El edificio tiene ascensor?",
        parse_mode="Markdown", reply_markup=kb_si_no("asc"))
    return ASC

async def get_asc(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    ctx.user_data["ascensor"] = q.data.endswith("_si")
    await q.edit_message_text(
        f"{'✅ Con' if ctx.user_data['ascensor'] else '❌ Sin'} ascensor\n\n"
        "📅 *4/8 — Antigüedad*\n\n¿Cuántos años de antigüedad tiene?",
        parse_mode="Markdown")
    return ANTIG

async def get_antig(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["antiguedad"] = int(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ Solo el número. Ej: *30*", parse_mode="Markdown")
        return ANTIG
    await u.message.reply_text(
        "🔧 *5/8 — Estado constructivo*",
        parse_mode="Markdown", reply_markup=kb_estado())
    return ESTADO

async def get_estado(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    val_str = q.data.split("_", 1)[1]
    ctx.user_data["estado_coef"]  = float(val_str)
    from coefs import ESTADO_LABELS
    ctx.user_data["estado_label"] = ESTADO_LABELS.get(val_str, val_str)
    await q.edit_message_text(
        f"Estado: {ctx.user_data['estado_label']}\n\n"
        "📐 *6/8 — Superficie cubierta (m²)*\n_Ej: 41.08_",
        parse_mode="Markdown")
    return SCUB

async def get_scub(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["sup_cub"] = float(u.message.text.strip().replace(",", "."))
    except ValueError:
        await u.message.reply_text("⚠️ Solo el número. Ej: *41.08*", parse_mode="Markdown")
        return SCUB
    await u.message.reply_text(
        "Superficie *semi cubierta* (m²) — escribí *0* si no tiene:",
        parse_mode="Markdown")
    return SSEMI

async def get_ssemi(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["sup_semi"] = float(u.message.text.strip().replace(",", "."))
    except ValueError:
        ctx.user_data["sup_semi"] = 0
    await u.message.reply_text(
        "Superficie *descubierta/patio* (m²) — escribí *0* si no tiene:",
        parse_mode="Markdown")
    return SDESC

async def get_sdesc(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["sup_desc"] = float(u.message.text.strip().replace(",", "."))
    except ValueError:
        ctx.user_data["sup_desc"] = 0
    await u.message.reply_text(
        "🚗 *7/8 — Cochera*\n\n¿Tiene cochera?",
        parse_mode="Markdown", reply_markup=kb_si_no("coch"))
    return COCH

async def get_coch(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    if q.data.endswith("_si"):
        await q.edit_message_text("¿Valor de la cochera en USD?", parse_mode="Markdown")
        return COCHVAL
    ctx.user_data["cochera"] = 0
    await q.edit_message_text(
        "⏳ *8/8 — Días en el mercado*\n_(0 si aún no está publicada)_",
        parse_mode="Markdown")
    return DIAS

async def get_cochval(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["cochera"] = float(u.message.text.strip().replace(",", "."))
    except ValueError:
        ctx.user_data["cochera"] = 0
    await u.message.reply_text(
        "⏳ *8/8 — Días en el mercado*\n_(0 si aún no está publicada)_",
        parse_mode="Markdown")
    return DIAS

async def get_dias(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["dias"] = int(u.message.text.strip())
    except ValueError:
        ctx.user_data["dias"] = 0
    await u.message.reply_text(
        "📍 *Coeficiente de Ubicación (Ub.)*\n"
        "Comparando el barrio del tasado con los comparables:",
        parse_mode="Markdown", reply_markup=kb_ub())
    return UB

async def get_ub(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    ctx.user_data["ub_coef"] = float(q.data.split("_")[1])
    d = ctx.user_data
    from coefs import calc_sup_homolog, calc_piso_coef, calc_sup_coef, calc_dias_coef, calc_coef_total
    sup_h = calc_sup_homolog(d["sup_cub"], d["sup_semi"], d["sup_desc"])
    pc    = calc_piso_coef(d["piso"], d["ascensor"])
    sc    = calc_sup_coef(d["sup_cub"])
    dc    = calc_dias_coef(d["dias"])
    ct    = calc_coef_total(d["ub_coef"], pc, 1.0, sc, d["estado_coef"], d["estado_coef"], dc)
    await q.edit_message_text(
        "✅ *Datos del tasado cargados*\n\n"
        f"📍 {d['direccion']}\n"
        f"🏢 Piso {d['piso']}° | {'Con' if d['ascensor'] else 'Sin'} ascensor\n"
        f"📐 Cub: {d['sup_cub']}m² | Semi: {d['sup_semi']}m² | Desc: {d['sup_desc']}m²\n"
        f"   _Homolog: {sup_h} m²_\n"
        f"📅 {d['antiguedad']} años | {d['dias']} días\n"
        f"🔧 {d['estado_label']}\n"
        f"📊 Coef estimado: *{ct}*\n\n"
        "─────────────────────────\n"
        "Pegá los *links de los comparables* (uno por línea).\n"
        "Cuando termines enviá /generar",
        parse_mode="Markdown")
    return LINKS

async def recibir_links(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if "links" not in ctx.user_data:
        ctx.user_data["links"] = []
    nuevos = [l.strip() for l in u.message.text.split("\n") if l.strip().startswith("http")]
    ctx.user_data["links"].extend(nuevos)
    n = len(ctx.user_data["links"])
    await u.message.reply_text(
        f"✅ *{n} link{'s' if n!=1 else ''} cargado{'s' if n!=1 else ''}*\n"
        "Podés agregar más o enviá /generar",
        parse_mode="Markdown")
    return LINKS

async def generar(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    links = ctx.user_data.get("links", [])
    if not links:
        await u.message.reply_text("⚠️ No hay links. Pegá al menos uno.")
        return LINKS
    msg = await u.message.reply_text(f"⏳ Procesando {len(links)} comparable{'s' if len(links)!=1 else ''}...")
    from scraper import scrape_link
    from excel_gen import generar_excel
    comparables = []
    for i, link in enumerate(links):
        try:
            await msg.edit_text(f"⏳ Analizando {i+1}/{len(links)}...\n_{link[:55]}_", parse_mode="Markdown")
            d = scrape_link(link)
            if d: comparables.append(d)
        except Exception as e:
            logger.error(f"Error: {link} — {e}")
    if not comparables:
        await msg.edit_text("❌ No pude extraer datos. Verificá que los links sean avisos individuales.")
        return LINKS
    await msg.edit_text(f"📊 Generando Excel con {len(comparables)} comparables...")
    try:
        path = generar_excel(ctx.user_data, comparables)
        nombre = f"ACM_{ctx.user_data['direccion'][:20].replace(' ','_')}.xlsx"
        await msg.delete()
        with open(path, "rb") as f:
            await u.message.reply_document(
                document=f, filename=nombre,
                caption=(f"✅ *ACM listo*\n📍 {ctx.user_data['direccion']}\n"
                         f"📊 {len(comparables)} comparables\n"
                         "_Abrí en Excel para ver los valores calculados._"),
                parse_mode="Markdown")
        import os; os.remove(path)
    except Exception as e:
        logger.error(e)
        await msg.edit_text(f"❌ Error generando Excel: {e}")
        return LINKS
    ctx.user_data.clear()
    return ConversationHandler.END

async def cancelar(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await u.message.reply_text("❌ Cancelado. Enviá /nuevo\\_acm para empezar de nuevo.", parse_mode="Markdown")
    return ConversationHandler.END

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token: raise RuntimeError("Falta TELEGRAM_TOKEN en variables de entorno")
    app = Application.builder().token(token).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("nuevo_acm", nuevo_acm)],
        states={
            DIR:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dir)],
            PISO:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_piso)],
            ASC:     [CallbackQueryHandler(get_asc,    pattern="^asc_")],
            ANTIG:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_antig)],
            ESTADO:  [CallbackQueryHandler(get_estado, pattern="^est_")],
            SCUB:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_scub)],
            SSEMI:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ssemi)],
            SDESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sdesc)],
            COCH:    [CallbackQueryHandler(get_coch,   pattern="^coch_")],
            COCHVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cochval)],
            DIAS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dias)],
            UB:      [CallbackQueryHandler(get_ub,     pattern="^ub_")],
            LINKS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_links),
                      CommandHandler("generar", generar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("ayuda",   ayuda))
    app.add_handler(CommandHandler("generar", generar))
    app.add_handler(conv)
    logger.info("Bot ACM iniciado ✅")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
