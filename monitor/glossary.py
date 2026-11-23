"""Explicaciones en lenguaje simple para cada indicador, señal y gráfico del dashboard.

Cada entrada tiene:
  title    título del panel
  what     qué es (1 o más párrafos)
  read     cómo leerlo
  monitor  (opcional) cómo lo usa este monitor y qué umbral aplica

Los umbrales se leen de config.py, así que si los cambias allá el texto se actualiza solo.
"""

from __future__ import annotations

from . import config


def entries() -> dict[str, dict]:
    T = config.THRESHOLDS
    neg = lambda x: f"{x:.0f}%".replace("-", "−")  # noqa: E731

    base = {
        # ------------------------------------------------------------ resumen
        "semaforo": dict(
            title="Semáforo de entrada",
            what=["Cuenta cuántas de las 7 señales de fondo se cumplen hoy. Las señales buscan rasgos que "
                  "históricamente han aparecido cerca de los pisos del mercado: una caída grande, pánico, "
                  "pánico que empieza a ceder, ventas generalizadas, crédito que no se rompe, valoración "
                  "razonable y una Fed que se prepara para bajar tasas."],
            read=["0 a 2 puntos es rojo, 3 a 4 es amarillo y 5 o más es verde. Si una fuente falla, esa "
                  "señal queda “sin dato” y no suma ni resta.",
                  "No predice el piso exacto. Indica cuándo las condiciones se parecen a buenos momentos "
                  "de entrada del pasado."],
        ),
        "titular": dict(
            title="¿Qué dice este titular?",
            what=["Es el resumen del semáforo de entrada en una frase. Cambia según cuántas señales de fondo "
                  "se cumplen: con pocas es rojo, con 3 o 4 amarillo y con 5 o más verde.",
                  "Capitulación es el momento en que muchos inversionistas se rinden y venden a cualquier "
                  "precio, por miedo o porque necesitan liquidez. Se reconoce por un VIX muy alto, caídas "
                  "fuertes y ventas en casi todas las acciones a la vez."],
            read=["Suele marcar el final de una caída: cuando ya vendió casi todo el que quería vender, quedan "
                  "pocos vendedores y el precio puede rebotar. Por eso el monitor la busca antes de sugerir "
                  "entrar con todo.",
                  "Rojo no significa que el mercado vaya a caer, sino que todavía no aparecen los rasgos de "
                  "un piso. Amarillo sugiere entrar de a poco y verde que las condiciones se parecen a buenos "
                  "momentos de entrada del pasado."],
        ),
        "tramos": dict(
            title="Plan por tramos",
            what=["En vez de invertir todo de una vez, el monto se divide en tres partes que se invierten "
                  "a medida que el mercado cae o que el semáforo mejora. Así se reduce el riesgo de entrar "
                  "todo justo antes de una caída mayor."],
            read=["Cada tramo se activa cuando se cumple cualquiera de sus condiciones. La barra muestra "
                  "cuánto ha caído el S&P 500 respecto de la caída que pide el tramo.",
                  f"Si un tramo no se activa antes de la fecha límite ({config.TRANCHE_DEADLINE}), se "
                  "invierte igual: quedarse fuera del mercado esperando el momento perfecto suele costar "
                  "más que entrar en un momento imperfecto."],
        ),

        # ------------------------------------------------------------ mercado
        "spx": dict(
            title="S&P 500",
            what=["Índice de las ~500 empresas más grandes de EE.UU. Cada empresa pesa según su tamaño en "
                  "bolsa, así que las más grandes (Apple, Microsoft, Nvidia…) mueven más el índice.",
                  "Es la referencia del mercado accionario estadounidense. Comprar un fondo o ETF del "
                  "S&P 500 equivale a comprar un pedacito de todas esas empresas."],
            read=["El número está en puntos y por sí solo dice poco. Lo útil es cuánto cambia: la "
                  "variación de hoy y la de los últimos 5 días hábiles (una semana de bolsa)."],
        ),
        "spx_dd": dict(
            title="Caída desde máximo (drawdown)",
            what=["Cuánto ha caído el índice respecto de su punto más alto histórico. 0% significa que "
                  "está en máximos."],
            read=["Por convención, una caída de 10% se llama “corrección” y una de 20% “mercado bajista”. "
                  "Históricamente, las caídas grandes han sido buenas oportunidades de entrada a largo "
                  "plazo, aunque nunca se sabe de antemano dónde está el piso."],
            monitor=f"La señal “Drawdown” se cumple cuando la caída es de {neg(T['drawdown_pct'])} o más. "
                    "Los tramos también se activan por caída.",
        ),
        "ma200": dict(
            title="Media de 200 días y RSI",
            what=["La media móvil de 200 días es el promedio del precio de cierre de los últimos 200 días "
                  "hábiles (unos 10 meses). Suaviza el ruido diario y muestra la tendencia de fondo.",
                  "El RSI (índice de fuerza relativa) es un indicador de 0 a 100 que compara la fuerza de "
                  "las subidas con la de las bajadas de los últimos 14 días."],
            read=["Si el índice está sobre su media de 200 días, la tendencia de fondo es alcista; si está "
                  "bajo, es bajista. Una distancia muy negativa indica una caída rápida.",
                  "Un RSI bajo 30 se considera “sobrevendido” (se vendió muy fuerte en poco tiempo) y "
                  "sobre 70 “sobrecomprado”."],
        ),
        "vix": dict(
            title="VIX, el “índice del miedo”",
            what=["Mide cuánta volatilidad espera el mercado de opciones para el S&P 500 en los próximos "
                  "30 días, expresada como % anual. Sube cuando los inversionistas pagan más por "
                  "protegerse de caídas.",
                  "VIX/VIX3M compara el miedo a 1 mes con el miedo a 3 meses."],
            read=["Bajo 15 es calma, cerca de 20 hay incertidumbre, sobre 30 hay estrés y sobre 40 pánico. "
                  "En las crisis de 2008 y 2020 superó 80.",
                  "Normalmente VIX/VIX3M es menor que 1, porque el futuro lejano se ve más incierto. Si "
                  "pasa de 1, el miedo inmediato supera al de largo plazo, algo típico de un pánico agudo."],
            monitor=f"La señal “Pánico” se cumple con VIX sobre {T['vix_panic']:.0f} o VIX/VIX3M sobre "
                    f"{T['vix_term_panic']:.0f}.",
        ),
        "breadth": dict(
            title="Breadth (amplitud del mercado)",
            what=["Porcentaje de acciones del S&P 500 cuyo precio está sobre su propia media de 200 días. "
                  "Muestra si un movimiento es generalizado o lo explican unas pocas empresas."],
            read=["Sobre 70% el mercado está sano y parejo. Bajo 20% casi todo el mercado fue vendido "
                  "(un “washout”), algo que suele ocurrir cerca de los pisos."],
            monitor=f"La señal “Washout breadth” se cumple bajo {T['breadth_washout']:.0f}%.",
        ),
        "ndx_sox": dict(
            title="Nasdaq-100 y SOX",
            what=["El Nasdaq-100 reúne a las 100 mayores empresas no financieras del Nasdaq y está muy "
                  "cargado a tecnología. El SOX es el índice de semiconductores, es decir, de las empresas "
                  "que diseñan y fabrican chips."],
            read=["Ambos se mueven más que el S&P 500, en ambas direcciones. Su caída desde el máximo de los "
                  "últimos 3 años es un termómetro del ánimo del mercado hacia la tecnología y la IA."],
        ),
        "rsp_spy": dict(
            title="Amplitud: igual ponderación vs S&P 500",
            what=["RSP es un fondo que invierte lo mismo en cada una de las 500 empresas. SPY invierte según "
                  "el tamaño de cada una, como el índice. El gráfico divide uno por el otro y parte en 100."],
            read=["Si la línea baja, las empresas gigantes están subiendo más que la empresa promedio: el "
                  "mercado depende de pocos nombres. Si sube, el avance es más parejo."],
        ),
        "sox": dict(
            title="Semiconductores (SOX)",
            what=["Índice de las principales empresas de chips. Es un sector cíclico y muy ligado a la "
                  "inversión en inteligencia artificial."],
            read=["El gráfico muestra cuánto está bajo su máximo. Caídas de 20% o más son frecuentes en "
                  "este sector y suelen anticipar o acompañar las correcciones del mercado amplio."],
        ),

        # ------------------------------------------------------------ tasas y crédito
        "hy": dict(
            title="Spreads de crédito (High Yield e IG)",
            what=["El spread es la tasa extra que piden los inversionistas para prestarle a empresas, en "
                  "comparación con prestarle al gobierno de EE.UU. High Yield (HY) son empresas con peor "
                  "calificación de riesgo; Investment Grade (IG) son empresas sólidas.",
                  "Se mide en puntos base: 1 pb = 0.01%, así que 400 pb = 4% extra. OAS es un ajuste "
                  "técnico por cláusulas de rescate anticipado de los bonos."],
            read=["Si el spread sube, el mercado teme quiebras. En HY, 300 a 400 pb es normal, sobre 500 hay "
                  "estrés y sobre 800 crisis.",
                  "Cuando las acciones caen pero el crédito sigue tranquilo, la caída suele ser de ánimo y no "
                  "de problemas reales en las empresas."],
            monitor=f"La señal “Crédito estable” se cumple si el spread HY no subió en los últimos "
                    f"{T['hy_stable_days']} datos.",
        ),
        "t10": dict(
            title="Treasuries (bonos del gobierno de EE.UU.)",
            what=["Es la tasa que paga el gobierno de EE.UU. al pedir prestado a 10 o a 2 años. La de 10 "
                  "años es la tasa de referencia “sin riesgo” del mundo.",
                  "La tasa real descuenta la inflación esperada (se toma de los bonos indexados, TIPS). "
                  "pp = puntos porcentuales: pasar de 4.00% a 4.25% es subir 0.25 pp."],
            read=["Si las tasas suben, los bonos se vuelven más atractivos frente a las acciones y el valor "
                  "presente de las utilidades futuras de las empresas baja. Por eso tasas que suben rápido "
                  "suelen presionar a la bolsa."],
        ),
        "curve": dict(
            title="Curva de tasas",
            what=["Diferencia entre la tasa a 10 años y la tasa a 2 años (o a 3 meses). Normalmente es "
                  "positiva, porque prestar por más tiempo exige un premio mayor."],
            read=["Si se vuelve negativa (curva “invertida”), el mercado espera que la Fed baje tasas porque "
                  "anticipa una economía más débil. Históricamente la inversión ha precedido a las "
                  "recesiones, con un desfase variable de 6 a 24 meses.",
                  "La versión 10a − 3m es la que usa la Fed de Nueva York en su modelo de probabilidad de "
                  "recesión."],
        ),
        "fed": dict(
            title="Fed funds (tasa de la Reserva Federal)",
            what=["Es la tasa que fija la Reserva Federal, el banco central de EE.UU., para los préstamos de "
                  "un día entre bancos. Se publica como un rango, por ejemplo 4.25–4.50%.",
                  "Es la palanca principal de la política monetaria: bajarla abarata el crédito y suele "
                  "impulsar la economía y los precios de los activos."],
            read=["La tasa a 2 años refleja lo que el mercado espera de la Fed en ese plazo. Si está bajo la "
                  "tasa actual (2a − Fed negativo), el mercado espera recortes."],
            monitor=f"La señal “Fed hacia recortes” se cumple cuando 2a − Fed es menor que "
                    f"{T['fed_cut_bias']:.0f}.",
        ),

        # ------------------------------------------------------------ valoración y macro
        "pe_cape": dict(
            title="P/E y CAPE (valoración)",
            what=["El P/E (precio/utilidad) dice cuántos años de utilidades actuales se pagan al comprar el "
                  "índice. Un P/E de 25 significa pagar 25 veces la utilidad de un año.",
                  "El CAPE o P/E de Shiller usa el promedio de utilidades de 10 años ajustadas por "
                  "inflación, para que un mal o buen año no distorsione la cifra."],
            read=["Más alto significa más caro. La valoración sirve poco para adivinar el corto plazo, pero "
                  "explica bastante del retorno esperado a 10 años: comprar caro suele rendir menos."],
            monitor="La señal “Valoración” se cumple cuando el P/E está bajo su promedio de los últimos 10 años.",
        ),
        "erp": dict(
            title="Prima de riesgo (ERP)",
            what=["Compara lo que “rinden” las acciones con lo que rinde un bono sin riesgo. Se calcula como "
                  "la rentabilidad de las utilidades (1 dividido por el P/E) menos la tasa a 10 años."],
            read=["Mientras más alta, más compensación extra ofrecen las acciones por su riesgo. Si es baja "
                  "o negativa, las acciones están caras frente a los bonos. Es una aproximación simple, "
                  "útil para comparar contra su propia historia."],
        ),
        "wti_dxy": dict(
            title="Petróleo WTI y dólar DXY",
            what=["WTI es el precio del barril de petróleo de referencia en EE.UU. DXY mide el valor del "
                  "dólar frente a una canasta de monedas (euro, yen, libra y otras)."],
            read=["Un petróleo caro alimenta la inflación y le pone presión a las tasas. Un dólar fuerte "
                  "encarece la deuda en dólares del resto del mundo y suele apretar las condiciones "
                  "financieras globales."],
        ),
        "claims": dict(
            title="Solicitudes de desempleo",
            what=["Cantidad de personas que piden por primera vez el subsidio de desempleo en EE.UU. cada "
                  "semana. Es uno de los datos más rápidos sobre el mercado laboral."],
            read=["Entre 200 y 250 mil es un mercado laboral sano. Un alza sostenida, por ejemplo sobre "
                  "300 mil, indica que las empresas están despidiendo y suele anticipar una desaceleración."],
        ),
        "ai_basket": dict(
            title="Canasta IA",
            what=["Grandes empresas tecnológicas y compañías expuestas a la ola de inversión en "
                  "inteligencia artificial, incluidas algunas que la financian con deuda."],
            read=["Estas empresas pesan mucho en el S&P 500, así que su ánimo arrastra al índice. Si caen "
                  "mucho más que el mercado, el entusiasmo por la IA se está enfriando. Las barras comparan "
                  "la caída de cada una contra la mayor de la lista."],
        ),

        # ------------------------------------------------------------ señales
        "sig_drawdown": dict(
            title="Señal: Drawdown",
            what=["Se cumple cuando el S&P 500 cae lo suficiente desde su máximo histórico."],
            read=["Las compras hechas después de caídas grandes han tenido, en promedio, mejores retornos "
                  "a largo plazo que las hechas en máximos."],
            monitor=f"Umbral: caída de {neg(T['drawdown_pct'])} o más.",
        ),
        "sig_panic": dict(
            title="Señal: Pánico",
            what=["Se cumple cuando el VIX está muy alto o cuando el miedo a corto plazo supera al de largo "
                  "plazo (VIX/VIX3M sobre 1)."],
            read=["Los mejores momentos para comprar suelen coincidir con miedo extremo, cuando muchos "
                  "venden por necesidad o por nervios."],
            monitor=f"Umbral: VIX sobre {T['vix_panic']:.0f} o VIX/VIX3M sobre {T['vix_term_panic']:.0f}.",
        ),
        "sig_panic_fading": dict(
            title="Señal: Pánico cediendo",
            what=["Se cumple cuando, después de un episodio de miedo, el VIX ya bajó bastante desde su "
                  "máximo del último mes."],
            read=["Entrar cuando el miedo empieza a ceder suele ser más seguro que intentar comprar en el "
                  "peor día."],
            monitor=f"Umbral: VIX {neg(T['vix_off_peak_pct'])} o más bajo su máximo de 30 días. Solo cuenta "
                    "si ese máximo llegó al menos a 25.",
        ),
        "sig_washout": dict(
            title="Señal: Washout breadth",
            what=["Se cumple cuando muy pocas acciones siguen sobre su media de 200 días: casi todo el "
                  "mercado fue vendido."],
            read=["Las ventas tan generalizadas suelen agotar a los vendedores y aparecen cerca de los pisos."],
            monitor=f"Umbral: menos de {T['breadth_washout']:.0f}% de las acciones sobre su media de 200 días.",
        ),
        "sig_credit": dict(
            title="Señal: Crédito estable",
            what=["Se cumple cuando el spread de los bonos High Yield no está subiendo."],
            read=["Si el crédito aguanta mientras las acciones caen, el problema suele ser de ánimo y no de "
                  "quiebras reales. Un spread que se dispara es mala señal aunque las acciones parezcan baratas."],
            monitor=f"Umbral: el spread HY de hoy no es mayor que el de hace {T['hy_stable_days']} datos.",
        ),
        "sig_valuation": dict(
            title="Señal: Valoración",
            what=["Se cumple cuando el P/E del S&P 500 está bajo su promedio de los últimos 10 años."],
            read=["Comprar más barato que el promedio reciente mejora el retorno esperado a largo plazo."],
        ),
        "sig_fed": dict(
            title="Señal: Fed hacia recortes",
            what=["Se cumple cuando la tasa a 2 años está bajo la tasa de la Fed, es decir, cuando el mercado "
                  "espera que la Fed baje tasas."],
            read=["Los recortes abaratan el crédito y suelen apoyar a la bolsa, aunque a veces llegan porque "
                  "la economía ya se está debilitando."],
        ),
    }
    base.update(_history_entries())
    return base


def _history_entries() -> dict[str, dict]:
    eps = {e["id"]: e for e in config.HISTORY_EPISODES}

    def ep(i, text):
        e = eps.get(i)
        return f"{e['name']} (desde {e['start']}): {text}" if e else None

    episodes = [p for p in [
        ep("1929", "el gran crash de Wall Street y la Gran Depresión. El S&P 500 llegó a caer cerca de 86% "
                   "y tardó unos 25 años en recuperar su máximo nominal."),
        ep("1987", "el 19 de octubre el índice cayó más de 20% en un solo día. Fue un pánico técnico, sin "
                   "recesión detrás, y se recuperó en menos de dos años."),
        ep("2000", "estalla la burbuja de las empresas de internet. La caída fue lenta, de unos 49% en dos "
                   "años y medio, y castigó sobre todo a tecnología (el Nasdaq perdió cerca de 78%)."),
        ep("2008", "crisis financiera por hipotecas de mala calidad y quiebra de Lehman Brothers. El S&P 500 "
                   "cayó cerca de 57% hasta marzo de 2009 y los bancos fueron el epicentro."),
        ep("2018", "la Fed subía tasas y el mercado temía una desaceleración. Caída cercana a 20% en tres "
                   "meses, recuperada cuando la Fed dio un giro."),
        ep("2020", "la pandemia provocó la caída de 34% más rápida de la historia, en apenas un mes, y una "
                   "recuperación también récord gracias a estímulos masivos."),
        ep("2022", "la inflación alta obligó a la Fed a subir tasas muy rápido. Cayeron a la vez acciones y "
                   "bonos; el S&P 500 bajó cerca de 25% y el Nasdaq más de 30%."),
        "Actual: parte en el último máximo histórico del activo elegido, o en la fecha que indiques, para "
        "comparar lo que está pasando hoy con los episodios anteriores.",
    ] if p]

    return {
        "hist_modes": dict(
            title="Dos formas de comparar",
            what=["Por período: eliges activos y un rango de fechas, y los ves juntos en el mismo gráfico. "
                  "Sirve para responder “¿cómo se comportó el oro frente al S&P 500 durante 2008?”.",
                  "Comparar crisis: eliges un activo y lo ves en varios episodios superpuestos, todos "
                  "partiendo desde el mismo punto (el máximo antes de la caída). Sirve para responder "
                  "“¿esta caída se parece más a 2020 o a 2008?”."],
            read=["Los datos son cierres diarios de los últimos años y cierres semanales antes, para que la "
                  "página cargue rápido. Los precios de fondos y acciones incluyen dividendos reinvertidos."],
        ),
        "hist_activos": dict(
            title="Activos disponibles",
            what=["Índices: canastas de acciones que resumen un mercado. Russell 2000 son empresas "
                  "pequeñas de EE.UU.",
                  "Fondos y ETF: fondos que se compran como una acción. TLT invierte en bonos del Tesoro de "
                  "EE.UU. a más de 20 años, GLD en oro físico, EEM en mercados emergentes, ECH en Chile y XLF "
                  "en bancos y aseguradoras.",
                  "Materias primas: precios de los contratos futuros de petróleo y cobre. El cobre es clave "
                  "para la economía chilena.",
                  "Monedas: “Dólar / peso chileno” es cuántos pesos cuesta un dólar; si sube, el peso se "
                  "debilita. Lo mismo para el yen. “Euro / dólar” es cuántos dólares cuesta un euro."],
            read=["Puedes comparar hasta 6 activos a la vez. Cada uno tiene una historia de distinto largo: "
                  "si el rango parte antes de que existiera, la línea empieza más tarde."],
        ),
        "hist_medidas": dict(
            title="Medidas del gráfico",
            what=["Cambio %: cuánto subió o bajó cada activo desde el primer día del rango. Todos parten en "
                  "0%, así que se pueden comparar aunque tengan precios muy distintos.",
                  "Caída desde máximo: cuánto está cada activo bajo su máximo histórico en cada momento. "
                  "Muestra la profundidad y la duración de las crisis.",
                  "Valor: el precio o nivel tal cual. Útil para un solo activo."],
            read=["La escala logarítmica hace que una misma subida porcentual ocupe el mismo alto en todo el "
                  "gráfico (de 100 a 200 se ve igual que de 1.000 a 2.000). Es la forma correcta de mirar "
                  "períodos de muchos años."],
        ),
        "hist_stats": dict(
            title="Cómo leer la tabla",
            what=["Cambio: variación total entre el primer y el último día del rango.",
                  "Rentabilidad anual: el crecimiento compuesto por año que equivale a ese cambio total. Solo "
                  "se muestra si el rango dura al menos un año.",
                  "Peor caída: la mayor baja desde un máximo hasta un mínimo dentro del rango, con la fecha "
                  "del mínimo."],
            read=["Dos activos pueden terminar con el mismo cambio, pero el que tuvo una peor caída fue más "
                  "difícil de mantener en el camino."],
        ),
        "hist_episodios": dict(
            title="Episodios de crisis",
            what=["Cada línea parte en 0% el día del máximo del S&P 500 antes de la caída, y avanza en meses "
                  "desde ese día. Si eliges otro activo, se usa la misma fecha de inicio."] + episodes,
            read=["En la tabla, “Recuperación” son los meses que pasaron hasta volver al nivel inicial, "
                  "aunque sea después del final de la ventana. Puedes cambiar las fechas en monitor/config.py."],
        ),
    }


SIGNAL_KEYS = {
    "drawdown": "sig_drawdown", "panic": "sig_panic", "panic_fading": "sig_panic_fading",
    "washout": "sig_washout", "credit": "sig_credit", "valuation": "sig_valuation", "fed": "sig_fed",
}
