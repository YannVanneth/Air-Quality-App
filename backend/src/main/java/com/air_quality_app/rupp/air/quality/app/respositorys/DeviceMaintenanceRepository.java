package com.air_quality_app.rupp.air.quality.app.respositorys;

import com.air_quality_app.rupp.air.quality.app.models.DeviceMaintenanceModel;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DeviceMaintenanceRepository extends JpaRepository<DeviceMaintenanceModel, Long> {
}
