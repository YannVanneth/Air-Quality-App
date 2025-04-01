package com.air_quality_app.rupp.air.quality.app.respositorys;

import com.air_quality_app.rupp.air.quality.app.models.AlertsModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface AlertRepository extends JpaRepository<AlertsModel, Long> {
  
}
