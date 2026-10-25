"""Reproduce the book's hypothetical BRL scenarios using Python's Decimal.

Run next to normalized-scenarios.json. No network or third-party dependencies.
The realization percentage scales benefit only; all scenario costs stay fixed.
"""
import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path


def number(value, label):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be numeric, not boolean')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'{label} must be numeric') from exc
    if not result.is_finite():
        raise ValueError(f'{label} must be finite')
    return result


def money_cents(value, label):
    value = number(value, label)
    if value < 0 or value * 100 != (value * 100).to_integral_value():
        raise ValueError(f'{label} must be nonnegative BRL with at most two decimals')
    return value * 100


def evaluate(case, scenario_index=1, realization=100):
    if type(scenario_index) is not int or scenario_index not in (0, 1, 2):
        raise ValueError('scenario must be 0, 1 or 2')
    rate = number(realization, 'realization')
    if not 0 <= rate <= 100:
        raise ValueError('realization must be between 0 and 100 percent')
    period = case['period']
    if period not in ('month', 'year', 'cohort'):
        raise ValueError('period must be month, year or cohort')
    scenarios = case['scenarios']
    if len(scenarios) != 3:
        raise ValueError('exactly three scenarios are required')
    scenario = scenarios[scenario_index]
    benefit, variable, run, build = (
        money_cents(scenario[key], key)
        for key in ('benefit', 'variable_cost', 'run_cost', 'build_cost')
    )
    # Retain fractional cents until each displayed output is rounded. This
    # matches the reader: it annualizes the unrounded period net, then formats.
    period_cents = benefit * rate / 100 - variable - run
    horizon_cents = period_cents * (12 if period == 'month' else 1) - build
    brl = lambda cents: format((cents / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), '.2f')
    return {
        'case': case['case'], 'scenario': scenario_index,
        'scenario_name': scenario['name'], 'currency': 'BRL',
        'realization_percent': str(rate), 'period': period,
        'period_net_BRL': brl(period_cents),
        'horizon': 'six_month_cohort' if period == 'cohort' else 'first_year',
        'horizon_net_after_build_BRL': brl(horizon_cents),
        'assumptions_not_observed_returns': True,
        'note': 'Capacity equivalent is not cash saved. Realization scales benefit only; costs stay fixed. Cohort benefit already covers six active months per extra line.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Reproduce one hypothetical scenario from the Nubank study.')
    parser.add_argument('case', choices=[f'{n:02d}' for n in range(1, 21)])
    parser.add_argument('--scenario', type=int, choices=(0, 1, 2), default=1)
    parser.add_argument('--realization', default='100', help='Benefit realization percentage, from 0 to 100 (default: 100).')
    parser.add_argument('--models', type=Path, default=Path(__file__).with_name('normalized-scenarios.json'))
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.models.read_text(), parse_float=Decimal)
        if data.get('currency') != 'BRL':
            raise ValueError('model currency must be BRL')
        matches = [case for case in data['cases'] if case['case'] == args.case]
        if len(matches) != 1:
            raise ValueError('case must appear exactly once in the model file')
        result = evaluate(matches[0], args.scenario, args.realization)
    except (OSError, KeyError, TypeError, ValueError, InvalidOperation) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
