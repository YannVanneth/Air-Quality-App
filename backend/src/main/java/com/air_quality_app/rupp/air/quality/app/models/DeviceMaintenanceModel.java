package com.air_quality_app.rupp.air.quality.app.models;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.ZonedDateTime;

@Entity
@Setter
@Getter
@AllArgsConstructor
@NoArgsConstructor
@Table(name = "device_maintenance")
public class DeviceMaintenanceModel {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(columnDefinition = "BIGSERIAL")
    private Long maintenance_id;

    @ManyToOne
    @JoinColumn(name = "device_id")
    private DeviceModel device;

    private ZonedDateTime timestamp;

    @Column(columnDefinition = "TEXT")
    private String description;
}
