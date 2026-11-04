from datasheetdelta.core import extract,compare

def test_csv_extracts_fields_and_locations():
 data=b'Parameter,Value\nPressure,10 bar\nVoltage,24 V\n'; fields,w=extract('x.csv',data)
 assert len(fields)==2 and fields[0].source=='row 2' and not w

def test_compare_changed_added_removed_unchanged():
 a,_=extract('a.csv',b'Parameter,Value\nPressure,10 bar\nMaterial,Steel\n')
 b,_=extract('b.csv',b'Parameter,Value\nPressure,12 bar\nVoltage,24 V\n')
 result=compare('a.csv',a,'b.csv',b)
 statuses={x['parameter']:x['status'] for x in result['findings']}
 assert statuses=={'material':'removed','pressure':'changed','voltage':'added'}

def test_text_extraction():
 fields,_=extract('spec.txt',b'Material: Stainless steel\nVoltage: 24 V')
 assert {x.name for x in fields}=={'material','voltage'}
