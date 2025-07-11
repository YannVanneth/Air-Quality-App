'use client';

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle } from 'react-leaflet';
import L, { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocateFixed } from 'lucide-react';

L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const RecenterMap = ({ center }: { center: any }) => {
    const map = useMap();
    useEffect(() => {
        if (center) map.setView(center);
    }, [center, map]);
    return null;
};

export default function Map() {
    const [userLocation, setUserLocation] = useState<LatLngExpression>();

    function getCurrentLocation() {
        if (typeof window !== 'undefined' && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    setUserLocation([
                        position.coords.latitude,
                        position.coords.longitude
                    ]);
                },
                (error) => {
                    console.error("Geolocation error:", error);
                    setUserLocation([11.569901955661196, 104.88973109726786]);
                }
            );
        }
    }

    useEffect(() => {
        getCurrentLocation();
    }, []);

    if (!userLocation) return <p className="text-center text-gray-500 mt-4">Detecting location...</p>;

    return (
        <div className="rounded-2xl shadow-lg overflow-hidden h-[500px] w-full mt-6">

            <MapContainer
                center={userLocation}
                zoom={13}
                scrollWheelZoom={true}
                className="h-full w-full filter saturate-125 contrast-110"
            >
                <TileLayer
                    url="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
                />
                <Circle
                    center={userLocation}
                    radius={20}
                    pathOptions={{
                        color: '#3b82f6',
                        fillColor: '#93c5fd',
                        fillOpacity: 0.3,
                        weight: 1,
                        dashArray: '4 2',
                    }}
                />
                <RecenterMap center={userLocation} />
                <Marker position={userLocation}>
                    <Popup>
                        <div>
                            <h1>A6's Mini Air Quality</h1>
                            <ul>
                                <li>PM : 20</li>
                                <li>PM : 20</li>
                                <li>PM : 20</li>
                            </ul>
                        </div>
                    </Popup>
                </Marker>
            </MapContainer>
            <div className='relative right-3 bottom-20'>
                <div className='absolute right-0 bg-muted p-2 rounded-full' onClick={getCurrentLocation}>
                    <LocateFixed size={32} />
                </div>
            </div>
        </div>
    );
};

