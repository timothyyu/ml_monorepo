package ase.data;

import ase.util.Time;

public class ReutersAnnDate {
	public Integer period;
	public Long annDate;
	public Boolean announced;
	public String status;
	public Integer phase;
	public Long born;
	
	public ReutersAnnDate(Integer period, Boolean announced, Long annDate, String status, Integer phase, Long born) {
		super();
		this.period = period;
		this.announced = announced;
		this.annDate = annDate;
		this.status = status;
		this.phase = phase;
		this.born = born;
	}
	
	public Long estimateAnnTs(Exchange.Type exch) {
		if (announced)
			return annDate;
		else if (annDate == null)
			return null;
		else if (status == null || status.equals("T"))
			return Time.today(annDate);
		else if (phase == null)
			return Time.today(annDate);
		else if (phase == 1)
			return Exchange.openTime(annDate, exch) - Time.MILLIS_PER_HOUR / 2;
		else if (phase == 2)
			return Exchange.openTime(annDate, exch) + Time.MILLIS_PER_HOUR / 2;
		else if (phase == 3)
			return Exchange.closeTime(annDate, exch) + Time.MILLIS_PER_HOUR / 2;
		else
			throw new RuntimeException("We shouldn't have reached this point");
	}
	
	public Boolean alreadyAnnounced(Exchange.Type exch, long asof) {
		assert !announced;
		if (annDate == null)
			return false;
		else if (Time.today(annDate) > Time.today(asof))
			return false;
		else if (status == null || status.equals("T"))
			return null;
		else if (phase == null)
			return null;
		else if (phase == 1) {
			long ann = Exchange.openTime(annDate, exch) - Time.MILLIS_PER_HOUR / 2;
			return asof > ann;
		}
		else if (phase == 2) {
			long ann = Exchange.openTime(annDate, exch) + Time.MILLIS_PER_HOUR / 2;
			return asof > ann;
		}
		else if (phase == 3) {
			long ann = Exchange.closeTime(annDate, exch) + Time.MILLIS_PER_HOUR / 2;
			return asof > ann;
		}
		else
			throw new RuntimeException("We shouldn't have reached this point");
		
	}
}
