package com.air_quality_app.rupp.air.quality.app.respositorys;

import com.air_quality_app.rupp.air.quality.app.models.DeviceModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface DeviceRepository extends JpaRepository<DeviceModel, Long> {

}
