//CONTADOR DE PERSONAS - ONIET (PRUEBA DE BANCO - Arduino UNO R3 fisico)
/*
COMENTARIOS: version de prueba en protoboard: 2 sensores HC-SR04
(entrada/salida) + 2 pulsadores (SUMAR pin 6 / RESTAR pin 7). Todavia
sin la LCD conectada en este armado.

FIX cooldown: al pasar la mano rapido frente a un sensor, el eco
ultrasonico a veces se pierde por un instante (la mano cambia de
angulo constantemente), la lectura vuelve a dar "sin deteccion" por
uno o dos ciclos, y con una simple bandera de estado el siguiente
ciclo bueno volvia a contar - de ahi que una sola pasada rapida
contara como 2 o 3 personas. Se reemplazo la bandera por un COOLDOWN
por sensor: despues de cada conteo, ese sensor se ignora durante
COOLDOWN_MS aunque su lectura parpadee entre "detecta"/"no detecta".
*/

#define TRIG_1 2   // Sensor ENTRADA
#define ECHO_1 3
#define TRIG_2 4   // Sensor SALIDA
#define ECHO_2 5

#define BOTON_SUMAR   6
#define BOTON_RESTAR  7

#define UMBRAL_CM 20  // ajustado para pruebas de escritorio (ver charla previa)

// Tiempo minimo entre 2 conteos del MISMO sensor. Una persona/mano
// cruzando tarda bastante mas que esto en despejar el sensor del
// todo, asi que 800ms-1000ms filtra el parpadeo sin arriesgar perder
// a la proxima persona real.
#define COOLDOWN_MS 900

int personasPresentes = 0;

// Guardamos el momento (millis) del ULTIMO conteo de cada sensor,
// en vez de una simple bandera de estado.
unsigned long ultimoConteoEntrada = 0;
unsigned long ultimoConteoSalida  = 0;

unsigned long ultimoDebounceBoton = 0;
const unsigned long DEBOUNCE_BOTON = 300; // ms

void setup() {
  Serial.begin(9600);

  pinMode(TRIG_1, OUTPUT);
  pinMode(ECHO_1, INPUT);
  pinMode(TRIG_2, OUTPUT);
  pinMode(ECHO_2, INPUT);

  pinMode(BOTON_SUMAR,  INPUT_PULLUP);
  pinMode(BOTON_RESTAR, INPUT_PULLUP);

  Serial.println("Prueba de banco iniciada.");
  mostrarConteo();
}

void loop() {

//LECTURA DE SENSORES
  long distanciaEntrada = leerDistanciaCM(TRIG_1, ECHO_1);
  long distanciaSalida  = leerDistanciaCM(TRIG_2, ECHO_2);

  // Descomentar para ver las distancias crudas mientras calibrás:
  // Serial.print("Entrada: "); Serial.print(distanciaEntrada);
  // Serial.print(" cm   Salida: "); Serial.print(distanciaSalida); Serial.println(" cm");

//LOGICA SENSOR ENTRADA (con cooldown)
  if (distanciaEntrada > 0 && distanciaEntrada < UMBRAL_CM) {
    if (millis() - ultimoConteoEntrada > COOLDOWN_MS) {
      personasPresentes++;
      ultimoConteoEntrada = millis();
      Serial.println("Entrada detectada");
      mostrarConteo();
    }
  }

//LOGICA SENSOR SALIDA (con cooldown)
  if (distanciaSalida > 0 && distanciaSalida < UMBRAL_CM) {
    if (millis() - ultimoConteoSalida > COOLDOWN_MS) {
      if (personasPresentes > 0) personasPresentes--;
      ultimoConteoSalida = millis();
      Serial.println("Salida detectada");
      mostrarConteo();
    }
  }

//BOTONES DE CORRECCION MANUAL (con debounce simple)
  if (millis() - ultimoDebounceBoton > DEBOUNCE_BOTON) {
    if (digitalRead(BOTON_SUMAR) == LOW) {
      personasPresentes++;
      Serial.println("Correccion manual: +1");
      mostrarConteo();
      ultimoDebounceBoton = millis();
    }
    if (digitalRead(BOTON_RESTAR) == LOW) {
      if (personasPresentes > 0) personasPresentes--;
      Serial.println("Correccion manual: -1");
      mostrarConteo();
      ultimoDebounceBoton = millis();
    }
  }
}

//MIDE DISTANCIA EN CM CON UN SENSOR ULTRASONICO HC-SR04
long leerDistanciaCM(int pinTrig, int pinEcho) {
  digitalWrite(pinTrig, LOW);
  delayMicroseconds(2);
  digitalWrite(pinTrig, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinTrig, LOW);

  long duracion = pulseIn(pinEcho, HIGH, 30000); // timeout 30ms
  if (duracion == 0) return -1; // sin lectura valida

  long distanciaCM = duracion * 0.0343 / 2;
  return distanciaCM;
}

void mostrarConteo() {
  Serial.print("Personas presentes: ");
  Serial.println(personasPresentes);
}