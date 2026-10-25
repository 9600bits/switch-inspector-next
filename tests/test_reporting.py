"""Analysis and range contracts, using offline CLI samples only."""
import json
from pathlib import Path

import pytest

from assets import AssetError, expand_range
from backend import Api
from devices import Device
from reporting import analyze_device, build_report, render_body, render_document
from secure_collector import ANALYSIS_COMMANDS, DEFAULT_COMMANDS, Collection, inspect


@pytest.mark.parametrize('expression,expected', [
    ('192.168.1.0/30', ['192.168.1.1', '192.168.1.2']),
    ('192.168.1.1 - 3', ['192.168.1.1', '192.168.1.2', '192.168.1.3']),
    ('192.168.1.254 - 192.168.2.1', ['192.168.1.254', '192.168.1.255', '192.168.2.0', '192.168.2.1']),
    ('192.168.1.0-0', ['192.168.1.0']),
    ('192.168.1.255-192.168.1.255', ['192.168.1.255']),
])
def test_range_forms(expression, expected):
    assert expand_range(expression) == expected


@pytest.mark.parametrize('expression', ['192.168.1.10-1', '192.168.1.1-256', '::1-::2',
    '1.2.3.4-1.2.3.256', '1.2.3.01-10', '1.2.3.4', '1.2.3.4-5-6', '1.2.3.4/33',
    '10.0.0.0-255.255.255.255', '1.2.3.1-01'])
def test_invalid_range(expression):
    with pytest.raises(AssetError):
        expand_range(expression)


def test_range_limit_and_shared_fields(tmp_path):
    assert len(expand_range('10.0.0.0-10.0.15.255')) == 4096
    with pytest.raises(AssetError):
        expand_range('10.0.0.0-10.0.16.0')
    api = Api(tmp_path)
    record = dict(range='192.0.2.0-2', vendor='', port=2000, username='tester', password='secret', group='lab')
    assert api.add_range(record) == {'ok': True, 'added': 3, 'skipped': 0}
    assert api.add_range(record) == {'ok': True, 'added': 0, 'skipped': 3}
    for asset in api._store.assets:
        for field in ('vendor', 'port', 'username', 'password', 'group'):
            assert asset[field] == record[field]


def sample(vendor='huawei', cpu=10, memory=20, temp=40):
    outputs = {
        'display cpu-usage' if vendor == 'huawei' else 'display cpu-usage summary': f'CPU usage: {cpu}%',
        'display memory-usage' if vendor == 'huawei' else 'display memory': f'Memory usage: {memory}%' if vendor == 'huawei' else f'System memory: 100 {memory} 80',
        'display environment': f'1 sensor NORMAL {temp} 60 75' if vendor == 'huawei' else f'1 sensor {temp} 0 60 75',
        'display interface brief': 'GE1/0/1 up up\nGE1/0/2 down down\nGE1/0/3 *down down',
        'display alarm active' if vendor == 'huawei' else 'display alarm': 'No active alarms',
        'display logbuffer' if vendor == 'huawei' else 'display logbuffer reverse': 'Logging buffer configuration and contents: Current messages: 0',
        'display counters errors inbound': 'GE1/0/1 0 0',
        'display counters errors outbound': 'GE1/0/1 0 0',
    }
    if vendor == 'huawei':
        outputs['display device'] = 'FAN1 Present FAN Normal\nPWR1 Present POWER Normal'
    else:
        outputs.update({'display fan': '1 1 Normal', 'display power': '1 1 Normal'})
    return dict(host='192.0.2.1', name='sw', vendor=vendor, group='lab', status='ok', outputs=outputs)


@pytest.mark.parametrize('vendor', ['huawei', 'hp_comware'])
@pytest.mark.parametrize('value,expected', [(0, 'ok'), (79, 'ok'), (80, 'warn'), (89, 'warn'), (90, 'crit')])
def test_resource_thresholds(vendor, value, expected):
    analysis = analyze_device(sample(vendor, cpu=value, memory=value))
    assert analysis['items']['cpu']['status'] == expected
    assert analysis['items']['memory']['status'] == expected
    assert analysis['status'] == ('ok' if expected == 'ok' else 'warn')


@pytest.mark.parametrize('vendor', ['huawei', 'hp_comware'])
@pytest.mark.parametrize('value,expected', [(59, 'ok'), (60, 'warn'), (74, 'warn'), (75, 'crit')])
def test_temperature_thresholds(vendor, value, expected):
    assert analyze_device(sample(vendor, temp=value))['items']['temp']['status'] == expected


def test_sensor_status_ports_and_sn_do_not_invent_issues():
    row = sample()
    a = analyze_device(row)
    assert a['status'] == 'ok'  # link down and admin down are statistics, SN is optional.
    assert a['items']['ports']['data'] == dict(total=3, up=1, admin_down=1, link_down=1,
                                              notable=[{'name':'GE1/0/2','phy':'down','kind':'down'}])
    row['outputs']['display environment'] = '1 sensor ABNORMAL 35 60 75'
    assert analyze_device(row)['items']['temp']['status'] == 'crit'
    row = sample('hp_comware')
    row['outputs']['display environment'] = '1 sensor ABNORMAL 35 0 60 75 90'
    assert analyze_device(row)['items']['temp']['status'] == 'crit'


def test_missing_unsupported_unknown_and_zero_are_distinct():
    row = sample(cpu=0)
    row['outputs'].pop('display memory-usage')
    row['outputs']['display environment'] = 'Error: Unrecognized command'
    row['outputs']['display alarm active'] = 'different firmware text'
    a = analyze_device(row)
    assert a['status'] == 'unknown'
    assert a['items']['cpu']['data']['pct'] == 0
    assert a['items']['memory']['reason'] == 'not_collected'
    assert a['items']['temp']['reason'] == 'unsupported'
    assert a['items']['alarm']['reason'] == 'unrecognized'
    row['outputs']['display cpu-usage'] = 'CPU usage: 90%'
    assert analyze_device(row)['status'] == 'warn'  # confirmed issues win over missing metrics.
    for command in ('display logbuffer', 'display counters errors inbound'):
        row['outputs'][command] = command + '\nnew firmware format'
    a = analyze_device(row)
    assert a['items']['log']['status'] == 'unknown'
    assert a['items']['errors']['status'] == 'unknown'


def test_partial_errors_and_hardware_keep_confirmed_evidence():
    row = sample('hp_comware')
    row['outputs']['display fan'] = '1 1 Abnormal'
    row['outputs']['display power'] = '% Unrecognized command'
    row['outputs']['display counters errors inbound'] = 'GE1/0/1 7 2'
    row['outputs']['display counters errors outbound'] = 'Error: not supported'
    a = analyze_device(row)
    assert a['status'] == 'warn'
    assert a['items']['fanpower']['status'] == 'crit'
    assert a['items']['errors']['status'] == 'warn'
    assert a['items']['errors']['data']['ports'][0] == dict(port='GE1/0/1', inbound=9, outbound=None)


def test_alarm_log_zero_severity_and_counts():
    row = sample()
    row['outputs']['display alarm active'] = 'Index Level Description\n1 Major module failed'
    row['outputs']['display logbuffer'] = 'sw IFNET/0/STATE: emergency\nsw IFNET/4/STATE: warning\nsw IFNET/6/STATE: info'
    row['outputs']['display counters errors inbound'] = 'GE1/0/1 1 0'
    report = build_report(dict(id='test', total=1), [row])
    assert report['counts']['warn'] == 1
    assert next(i['count'] for i in report['issues'] if i['key'] == 'log') == 1
    assert report['devices'][0]['analysis']['items']['log']['data']['count'] == 2
    assert sum(i['count'] for i in report['issues']) == 3


def test_report_valid_samples_history_and_escaping(tmp_path):
    rows = [sample(cpu=0), dict(sample(), host='192.0.2.2', name='<img src=x onerror=alert(1)>',
                              status='fail', outputs={}, metrics={})]
    report = build_report(dict(id='old-run', total=4, state='cancelled'), rows)
    assert report['completed'] == 2 and report['remaining'] == 2
    assert report['counts'] == dict(ok=1, warn=0, unknown=0, fail=1)
    assert report['resources']['cpu']['valid'] == 1
    assert report['resources']['cpu']['top'][0]['value'] == 0
    assert report['ports']['total'] == 3
    body = render_body(report)
    assert '<img src=x' not in body and '&lt;img' in body
    assert 'None %' not in body
    document = render_document(report, rows, Path(__file__).parents[1] / 'ui')
    assert 'src="http' not in document and 'href="http' not in document
    api = Api(tmp_path)
    api._store.history = [dict(id='old-run', total=4, state='cancelled', results=rows)]
    api._store.save()
    folder = tmp_path / 'reports' / 'old-run'
    folder.mkdir(parents=True)
    path = folder / 'results.json'
    path.write_text(json.dumps(rows), encoding='utf-8')
    original = path.read_bytes()
    assert api.get_report('old-run')['counts'] == report['counts']
    assert api.get_result('192.0.2.2', 'old-run')['name'] == rows[1]['name']
    assert path.read_bytes() == original  # no asset needed and no old archive mutation.
    assert 'error' in api.get_report('../old-run')
    rows[0]['analysis'] = analyze_device(rows[0])
    rows[0]['outputs']['display cpu-usage'] = 'CPU usage: 99%'
    assert analyze_device(rows[0])['items']['cpu']['data']['pct'] == 0


def test_empty_and_all_failed():
    for rows in ([], [dict(host='192.0.2.1', vendor='', status='fail', error='timeout')]):
        report = build_report(dict(id='empty', total=3), rows)
        assert report['resources']['cpu']['valid'] == 0
        assert report['ports']['devices'] == 0
        assert 'None' not in render_body(report)


def test_top_ten_valid_samples_and_custom_command_issue():
    rows = [dict(sample(cpu=i), host=f'192.0.2.{i+1}') for i in range(12)]
    report = build_report(dict(id='top', total=12), rows)
    assert report['counts']['ok'] == 12
    assert report['resources']['cpu']['valid'] == 12
    assert [r['value'] for r in report['resources']['cpu']['top']] == list(range(11,1,-1))
    row = sample()
    row['outputs']['show example'] = '% Unrecognized command'
    a = analyze_device(row)
    assert a['status'] == 'unknown'
    assert a['command_issues'] == [dict(command='show example', reason='设备不支持')]


@pytest.mark.parametrize('vendor', ['huawei', 'hp_comware'])
def test_default_extension_persistence_and_unsupported_isolation(tmp_path, vendor):
    assert set(ANALYSIS_COMMANDS[vendor]).issubset(DEFAULT_COMMANDS[vendor])
    api = Api(tmp_path)
    custom = [dict(command='show version', enabled=False), dict(command='display cpu-usage', enabled=True)]
    api.save_commands(vendor, custom)
    assert Api(tmp_path).snapshot()['commands'][vendor] == custom
    calls = []
    row = sample(vendor)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def find_prompt(self): return '<sw>'
        def send_command(self, command, **kwargs):
            calls.append(command)
            if command == 'display version':
                return 'Huawei VRP Version 8' if vendor == 'huawei' else 'H3C Comware Version 7'
            if command == 'display environment': return 'Error: Unrecognized command'
            return row['outputs'].get(command, '')
    result = inspect(Device('sw', '192.0.2.1', vendor, 22, 'user', 'pass'), connector=lambda **kwargs: Connection())
    assert result.status == 'ok'
    assert result.command_status['display environment'] == 'unsupported'
    assert calls[-1] == 'display counters errors outbound'
    assert 'display device esn' not in calls and 'display device manuinfo' not in calls
