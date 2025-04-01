package com.air_quality_app.rupp.air.quality.app.models;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.ZonedDateTime;
import java.util.*;

@Entity
@Setter
@Getter
@AllArgsConstructor
@NoArgsConstructor
@Table(name = "devices")
public class DeviceModel {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(columnDefinition = "UUID")
    private UUID device_id;

    @Column(length = 255, nullable = false)
    private String name;

    @Column(name = "location_lat", precision = 9, scale = 6, nullable = false)
    private Double latitude;

    @Column(name = "location_lon", precision = 9, scale = 6, nullable = false)
    private Double longitude;

    private ZonedDateTime installed_at;

    @Column(length = 50, nullable = false)
    private String status;

    @OneToMany(mappedBy = "devices")
    private List<DeviceMaintenanceModel> device_maintenance;

    @OneToMany(mappedBy = "devices")
    private List<AlertsModel> alerts;

    @OneToMany(mappedBy = "devices")
    private List<SensorDataModel> sensor_data;
}
