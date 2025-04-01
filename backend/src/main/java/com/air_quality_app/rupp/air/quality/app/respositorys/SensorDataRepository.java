package com.air_quality_app.rupp.air.quality.app.respositorys;

import com.air_quality_app.rupp.air.quality.app.models.SensorDataModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SensorDataRepository extends JpaRepository<SensorDataModel, Long> {

}
