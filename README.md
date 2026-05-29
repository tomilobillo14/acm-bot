# Bot ACM Inmobiliario

Bot de Telegram para automatizar el Análisis Comparativo de Mercado (ACM) en tasaciones inmobiliarias.

## ¿Qué hace?

1. Te guía paso a paso para cargar los datos de la propiedad del cliente (tasado)
2. Recibe links de portales inmobiliarios (Zonaprop, Argenprop, MercadoLibre)
3. Extrae automáticamente los datos de cada comparable
4. Calcula los coeficientes correctores según la tabla oficial
5. Genera y te envía el Excel ACM completo directamente en el chat

## Archivos

| Archivo | Descripción |
|---|---|
| `main.py` | Lógica del bot y flujo de conversación |
| `scraper.py` | Extracción de datos de portales |
| `excel_gen.py` | Generación del Excel ACM |
| `coefs.py` | Tabla de coeficientes correctores |
| `TEMPLATE.xlsx` | Plantilla Excel base |
| `requirements.txt` | Dependencias Python |
| `Procfile` | Configuración de proceso para Railway |

## Deploy en Railway

### Paso 1 — Variables de entorno
En Railway → tu proyecto → Variables, agregá:
```
TELEGRAM_TOKEN = tu_token_de_botfather
```

### Paso 2 — Deploy
Railway detecta automáticamente el `Procfile` y ejecuta `python main.py`.

## Comandos del bot

| Comando | Acción |
|---|---|
| `/start` | Bienvenida |
| `/nuevo_acm` | Iniciar un ACM nuevo |
| `/generar` | Procesar links y generar el Excel |
| `/cancelar` | Cancelar el proceso actual |
| `/ayuda` | Ver instrucciones |

## Portales compatibles

- Zonaprop
- Argenprop  
- MercadoLibre Inmuebles
