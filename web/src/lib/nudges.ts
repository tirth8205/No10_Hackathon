// Days-to-approval estimates for the "Getting paid" banner (spec 11.6).
// The return figure is a minimum: it adds one return, but not the time it takes
// to get a new letter, and the new letter could be returned again.

export const NUDGES = {
  /** Illustrative, based on published LAA civil processing times. */
  baselineWorkingDays: 13,
  /** Placeholder assumption for one return loop. Replace with LAA data. */
  returnLoopWorkingDays: 10,
};

export const daysIfRight = NUDGES.baselineWorkingDays;
export const minDaysIfReturned = NUDGES.baselineWorkingDays + NUDGES.returnLoopWorkingDays;
export const minDaysSaved = NUDGES.returnLoopWorkingDays;

export const ESTIMATE_NOTE =
  `Estimates. ${daysIfRight} days is based on published LAA processing times. ` +
  `${minDaysIfReturned} days adds one return but not the time it takes to get a new letter, so it could be longer.`;
