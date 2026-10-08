//CONTADOR DE PERSONAS - ONIET (PRUEBA DE BANCO - Arduino UNO R3 fisico)
/*
COMENTARIOS: 2 sensores HC-SR04 (entrada/salida) + 2 pulsadores
(SUMAR pin 6 / RESTAR pin 7) + buzzer ACTIVO en pin 8 para
confirmacion sonora en cada entrada/salida detectada.

Un buzzer activo ya trae su propio oscilador adentro: solo se prende
y apaga con HIGH/LOW, no se le puede variar el tono (no usa tone()).
Por eso entrada y salida suenan igual - se diferencian por la
cantidad de pitidos, no por el tono: 1 beep = entrada, 2 beeps
cortos = salida.

Cooldown por sensor para evitar contar de mas al pasar la mano
rapido (ver charla previa).
*/

#define TRIG_1 2   // Sensor ENTRADA
#define ECHO_1 3
#define TRIG_2 4   // Sensor SALIDA
#define ECHO_2 5

#define BOTON_SUMAR   6
#define BOTON_RESTAR  7

#define BUZZER 8

#define UMBRAL_CM 120
#define COOLDOWN_MS 1300

int personasPresentes = 0;

unsigned long ultimoConteoEntrada = 0;
unsigned long ultimoConteoSalida  = 0;
unsigned long ultimoDebounceBoton = 0;
const unsigned long DEBOUNCE_BOTON = 300;

void setup() {
  Serial.begin(9600);

  pinMode(TRIG_1, OUTPUT); pinMode(ECHO_1, INPUT);
  pinMode(TRIG_2, OUTPUT); pinMode(ECHO_2, INPUT);
  pinMode(BOTON_SUMAR,  INPUT_PULLUP);
  pinMode(BOTON_RESTAR, INPUT_PULLUP);
  pinMode(BUZZER, OUTPUT);

  Serial.println("Prueba de banco iniciada.");
  mostrarConteo();
}

void loop() {
  long distanciaEntrada = leerDistanciaCM(TRIG_1, ECHO_1);
  long distanciaSalida  = leerDistanciaCM(TRIG_2, ECHO_2);

//LOGICA SENSOR ENTRADA (con cooldown)
  if (distanciaEntrada > 0 && distanciaEntrada < UMBRAL_CM) {
    if (millis() - ultimoConteoEntrada > COOLDOWN_MS) {
      personasPresentes++;
      ultimoConteoEntrada = millis();
      Serial.println("Entrada detectada");
      beepEntrada();
      mostrarConteo();
    }
  }

//LOGICA SENSOR SALIDA (con cooldown)
  if (distanciaSalida > 0 && distanciaSalida < UMBRAL_CM) {
    if (millis() - ultimoConteoSalida > COOLDOWN_MS) {
      if (personasPresentes > 0) personasPresentes--;
      ultimoConteoSalida = millis();
      Serial.println("Salida detectada");
      beepSalida();
      mostrarConteo();
    }
  }

//BOTONES MANUALES: SUMAR = entrada, RESTAR = salida (con debounce simple)
  if (millis() - ultimoDebounceBoton > DEBOUNCE_BOTON) {
    if (digitalRead(BOTON_SUMAR) == LOW) {
      personasPresentes++;
      ultimoDebounceBoton = millis();
      Serial.println("Entrada detectada");
      mostrarConteo();
    }
    if (digitalRead(BOTON_RESTAR) == LOW) {
      if (personasPresentes > 0) personasPresentes--;
      ultimoDebounceBoton = millis();
      Serial.println("Salida detectada");
      mostrarConteo();
    }
  }
}

//MIDE DISTANCIA CON HC-SR04
long leerDistanciaCM(int pinTrig, int pinEcho) {
  digitalWrite(pinTrig, LOW); delayMicroseconds(2);
  digitalWrite(pinTrig, HIGH); delayMicroseconds(10);
  digitalWrite(pinTrig, LOW);
  long duracion = pulseIn(pinEcho, HIGH, 30000);
  if (duracion == 0) return -1;
  return duracion * 0.0343 / 2;
}

void mostrarConteo() {
  Serial.print("Personas presentes: ");
  Serial.println(personasPresentes);
}

//SONIDOS - version BUZZER ACTIVO (1 beep = entrada, 2 beeps = salida)
void beepEntrada() {
  digitalWrite(BUZZER, HIGH);
  delay(100);
  digitalWrite(BUZZER, LOW);
}

void beepSalida() {
  digitalWrite(BUZZER, HIGH);
  delay(80);
  digitalWrite(BUZZER, LOW);
  delay(80);
  digitalWrite(BUZZER, HIGH);
  delay(80);
  digitalWrite(BUZZER, LOW);
}