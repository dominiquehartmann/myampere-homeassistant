# myAmpere für Home Assistant

Eine Home-Assistant-Integration für [myAmpere](https://github.com/dominiquehartmann/myampere), die lokale App für
Solaranlagen mit Heimspeicher. Sie zeigt die Werte deiner Anlage in Home Assistant, auch im Energie-Dashboard, und kann
auf deinen Wunsch den Speicher und die eigenen Geräte steuern.

Die Integration ist nur ein Client: Sie funktioniert nur, solange ein myAmpere-Server in deinem Netzwerk läuft. Sie
spricht die externe Schnittstelle des Servers an und nie den Wechselrichter. Jeder Befehl läuft über dieselben Prüfungen
wie in der myAmpere-App (Steuerschalter, Testmodus, Grenzen), und der Server protokolliert ihn mit dem Namen des
Zugangs.

Diese Integration hat nichts mit dem Ursprungsprojekt OpenAmpere oder mit dem Unternehmen zu tun, das die Anlagen
verkauft hat (EKD). Die Nutzung erfolgt auf eigene Verantwortung; das ist keine rechtliche oder elektrotechnische
Beratung.

## Voraussetzungen

- Ein laufender myAmpere-Server (Docker oder die Home-Assistant-App), den Home Assistant erreicht.
- Home Assistant mit HACS oder den Ordner `custom_components/myampere` von Hand kopieren.

## Installation

1. In HACS das Menü öffnen, „Benutzerdefinierte Repositories“ wählen und
   `https://github.com/dominiquehartmann/myampere-homeassistant` als Integration hinzufügen. Dann myAmpere installieren.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → myAmpere öffnen.
4. In der myAmpere-App unter Mehr → Verbindung einen Verbindungscode für Home Assistant erzeugen und in die Integration
   eintragen. Kopplung, Zugang und Zertifikat speichert Home Assistant danach.

Zeigt der Server ein neues Zertifikat, koppelst du neu: Die Integration akzeptiert ein geändertes Zertifikat nie von
allein.

## Entitäten

Die Integration bietet alles, was die offizielle OpenAmpere-Integration anbietet: Leistungs-, Energie- und
Temperatursensoren, Batteriemodus und -grenzen, Netzladen, den Modus der eigenen Geräte und der Wallboxen, die myAmpere
selbst steuert.

Dazu kommen der Strompreis Import der aktuellen Viertelstunde, die Solarprognose für heute und morgen und die nächste
geplante Ladeviertelstunde mit ihrem Grund. Diese sind standardmäßig aus: Schalte in den Einstellungen des Geräts die
ein, die du brauchst.

Weitere Entitäten kommen Schritt für Schritt, sobald der Server mehr Daten anbietet.

## Entwicklung

Die Tests laufen in einer eigenen Umgebung mit festgelegten Versionen:

    cd tests
    uv venv ../.venv-ha --python 3.14
    uv pip install -p ../.venv-ha -r requirements.lock
    ../.venv-ha/bin/pytest

Issues und Pull Requests sind willkommen. Beschreibe bitte, was der Server geantwortet hat und welche Version von
myAmpere du nutzt.

## Lizenz

MIT. Siehe [LICENSE](LICENSE).
