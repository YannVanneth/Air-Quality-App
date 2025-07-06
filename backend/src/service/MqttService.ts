import mqtt, { MqttClient } from "mqtt";



export class MqttService {

    private client: MqttClient;
    private readonly host: string = 'mqtt://localhost:1883';


    constructor() {
        this.client = mqtt.connect(this.host);


        this.client.on('connect', () => {
            console.log('[MQTT] Connected to broker at', this.host);
        });

        this.client.on('error', (err) => {
            console.error('[MQTT] Connection error :', err);
            this.client.end();
        });


        this.client.on('reconnect', () => {
            console.log('[MQTT] reconnecting');
        });

        this.client.on('message', (topic, message) => {
            console.log(`[MQTT] Received on ${topic}: ${message.toString()}`);
        });
    }

    public publish(topic: string, message: string): void {
        this.client.publish(topic, message, {}, (err) => {
            if (err) {
                console.error('[MQTT] Publish error:', err);
            }
        });
    }

    public subscribe(topic: string): void {
        this.client.subscribe(topic, (err) => {
            if (err) {
                console.error('[MQTT] Subscribe error:', err);
            } else {
                console.log(`[MQTT] Subscribed to ${topic}`);
            }
        });
    }

    public disconnect(): void {
        this.client.end(() => {
            console.log('[MQTT] Disconnected from broker');
        });





    }


}



