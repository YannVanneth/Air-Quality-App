import express, { Request, Response } from 'express';
import mqtt, { MqttClient } from 'mqtt/*';
import { MqttService } from './service/MqttService';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get('/', (req: Request, res: Response) => {
    res.send('Hello Group 02');
});


const mqttService = new MqttService();

mqttService.subscribe('test/topics');

setTimeout(() => {
    mqttService.publish('test/topic', 'Hello from TypeScript MQTT client');
}, 1000);

process.on('SIGINT', () => {
    mqttService.disconnect();
    process.exit();
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
