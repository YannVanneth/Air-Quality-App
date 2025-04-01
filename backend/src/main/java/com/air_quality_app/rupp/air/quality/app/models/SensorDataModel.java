package com.air_quality_app.rupp.air.quality.app.models;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.ZonedDateTime;

@Entity
@Setter
@Getter
@AllArgsConstructor
@NoArgsConstructor
@Table(name = "sensor_data")
public class SensorDataModel {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(columnDefinition = "BIGSERIAL")
    private Long data_id;

    @ManyToOne
    @JoinColumn(name = "device_id")
    private DeviceModel device;

    private ZonedDateTime timestamp;

    @Column(precision = 6, scale = 2)
    private BigDecimal pm2_5;

    @Column(precision = 6, scale = 2)
    private BigDecimal pm10;

    @Column(precision = 6, scale = 2)
    private BigDecimal co;

    @Column(precision = 6, scale = 2)
    private BigDecimal co2;

    @Column(precision = 5, scale = 2)
    private BigDecimal temperature;

    @Column(precision = 5, scale = 2)
    private BigDecimal humidity;

    @Column(precision = 6, scale = 2)
    private BigDecimal o3;

    @Column(precision = 6, scale = 2)
    private BigDecimal no2;

    @Column(precision = 6, scale = 2)
    private BigDecimal so2;

}
