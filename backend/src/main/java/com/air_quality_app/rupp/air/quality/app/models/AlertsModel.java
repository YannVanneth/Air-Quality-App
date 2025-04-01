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
@Table(name = "alerts")
public class AlertsModel {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(columnDefinition = "BIGSERIAL")
    private Long alert_id;

    @ManyToOne
    @JoinColumn(name = "device_id", nullable = false)
    private DeviceModel device;

    private ZonedDateTime timestamp;

    @Column(columnDefinition = "TEXT")
    private String messages;

    @Column(length = 20)
    private String severity;

    private boolean resolved;
}
