import re
import os.path

with open("../tables.sql", "r") as f:
    content: str = f.read()
    tables = re.findall(r'CREATE\sTABLE\s(.+)\n\(\n\s+([A-Za-z\s\(0-9À-ÿ\)_,\'\"-.’]+)\n\);', content)

    for table in tables:
        table_name = table[0].lower()
        table_lines = table[1].split(',\n')
        sanitize_table_lines = []

        import_list = ['Column']
        import_content = "import models\n"

        for line in table_lines:

            type_line = ''
            constraint_line = ''
            line = line.lower().strip()

            # Ajoute la clé de contrainte unique si elle existe
            if 'constraint' in line:
                if 'unique' in line:
                    constraint_unique_line = ''
                    constraint_unique = re.findall(r'constraint\s(.*)\sunique\s\((.*)\)', line)
                    constraint_unique_name = f"'{constraint_unique[0][0].upper()}'"
                    constraint_unique_tables = constraint_unique[0][1].split(',')
                    for constraint_unique_table in constraint_unique_tables:
                        constraint_unique_line += f"'{constraint_unique_table}', "
                    constraint_line += f"    __table_args__ = (\n" \
                                       f"        UniqueConstraint({constraint_unique_line} name={constraint_unique_name}),\n" +\
                                       "        {},\n" \
                                       "    )"
                    import_list.append('UniqueConstraint')
                continue

            line = re.sub('not null', 'nullable=False', line)

            if 'collate unicode' in line or 'collate unicode_ci' in line:
                line = line.replace(" collate unicode_ci", "")
                line = line.replace(" collate unicode", "")

            if 'default' in line:
                default_value = re.findall(r'default\s([\'\w-]+)', line)[0]
                if re.match(r'x\'[a-z\d]{32}\'', default_value) is not None:
                    if default_value == 'x\'cb47d065a4982b409401c21608f936d6\'':
                        line = re.sub(r'\sdefault\s([\'\w-]+)', ' default=NULL_ID', line)
                        if 'NULL_ID' not in import_content:
                            import_content += "from models import NULL_ID\n"
                    else:
                        hex_value = re.findall(r'x\'([a-z\d]{32})\'', line)
                        line = re.sub(r'\sdefault\s([\'\w-]+)', f' default=uuid.UUID(hex=\'{hex_value[0]}\')', line)
                        if 'import uuid' not in import_content:
                            import_content += "import uuid\n"

                elif default_value == 'current_date':
                    line = re.sub(r'\sdefault\s([\'\w-]+)', ' default=datetime.now().date()', line)
                    if 'datetime' not in import_content:
                        import_content += "from datetime import datetime\n"
                # necessaire car dans la BDD, CURRENT_TIME est suivi d'un espace en plus
                elif default_value == 'current_time':
                    line = re.sub(r'\sdefault\s([\'\w-]+\s)', ' default=datetime.now().date()', line)
                    if 'datetime' not in import_content:
                        import_content += "from datetime import datetime\n"
                elif default_value == 'null':
                    line = re.sub(r'\sdefault\s([\'\w-]+)', ' default=None', line)
                elif 'd_bool' in line:
                    if default_value == '1':
                        default_value = True
                    if default_value == '0':
                        default_value = False
                    line = re.sub(r'\sdefault\s([\'\w-]+)', f' default={default_value}', line)
                else:
                    line = re.sub(r'\sdefault\s([\'\w-]+)', r' default=\1', line)

            if 'char' in line or 'varchar' in line or 'blob sub_type 1' in line:
                line = re.sub('char|varchar|blob sub_type 1', 'String', line)
                type_line = 'str'
                if import_list.count('String') == 0:
                    import_list.append('String')

            if 'd_lib50' in line or 'd_lib60' in line:
                line = re.sub(r'd_lib([\d]{2})', r'String(\1)', line)
                type_line = 'str'
                if import_list.count('String') == 0:
                    import_list.append('String')

            if 'd_uuid' in line:
                line = re.sub(r'd_uuid[n]?', 'models.UUID', line)
                type_line = 'models.UUID'

            if 'date' in line or 'time' in line:
                line = re.sub(r'\sdate', r' Date', line)
                line = re.sub(r'\stime', r' Date', line)
                type_line = 'Date'
                if import_list.count('Date') == 0:
                    import_list.append('Date')

            if 'integer' in line or 'd_numfiche' in line:
                line = re.sub('integer', 'Integer', line)
                line = re.sub('d_numfiche', 'Integer', line)
                type_line = 'int'
                if import_list.count('Integer') == 0:
                    import_list.append('Integer')

            if 'bigint' in line:
                line = re.sub('bigint', 'BIGINT', line)
                type_line = 'int'
                if import_list.count('BIGINT') == 0:
                    import_list.append('BIGINT')

            if 'smallint' in line or 'd_id_small' in line or 'd_SmallInteger' in line:
                line = re.sub('smallint', 'SmallInteger', line)
                line = re.sub('d_id_small', 'SmallInteger', line)
                line = re.sub('d_SmallInteger', 'SmallInteger', line)
                type_line = 'int'
                if import_list.count('SmallInteger') == 0:
                    import_list.append('SmallInteger')

            if 'numeric' in line:
                line = re.sub(r'numeric\(([0-9]{2}),', r'Numeric(\1 ', line)
                type_line = 'float'
                if import_list.count('Numeric') == 0:
                    import_list.append('Numeric')

            if 'decimal' in line:
                if 'd_decimal' in line:
                    line = re.sub('d_decimal', 'DECIMAL', line)
                else:
                    line = re.sub(r'decimal\(([0-9]{0,2}),', r'DECIMAL(\1 ', line)
                type_line = 'float'
                if import_list.count('DECIMAL') == 0:
                    import_list.append('DECIMAL')

            if 'd_bool' in line:
                line = re.sub('d_bool', 'Boolean', line)
                type_line = 'bool'
                if import_list.count('Boolean') == 0:
                    import_list.append('Boolean')

            if 'nullable=False' not in line and 'UUID' not in line:
                type_line = f'Optional[{type_line}]'
                if 'Optional' not in import_content:
                    import_content += "from typing import Optional\n"

            line_elements = line.split(' ')
            column_name = ''
            line_elements[0] = line_elements[0].strip('"')
            if f"{table_name.replace('agde_', '')}_id" == line_elements[0]:
                column_name = f'id: {type_line}'
            elif re.match(r'import', line_elements[0]) is not None:
                column_name = f'is_import: {type_line}'
            else:
                column_name = f"{line_elements[0]}: {type_line}"
            line_elements[0] = f'\'{line_elements[0]}\''
            line = ', '.join(line_elements)
            if table_name.replace('agde_', '') in line_elements[0] and 'id' in line_elements[0]:
                line = f'Column({line}, primary_key=True)'
            else:
                line = f'Column({line})'
            line = f'{column_name} = {line}'

            if "default=', '" in line:
                line = re.sub("default=', '", 'default=None', line)

            sanitize_table_lines.append(line)

        save_path = '/home/encinas/Documents/Workspace/Python/test_mappage_table_agde/models'
        import_content += f"from sqlalchemy import {', '.join(import_list)}\n\n\n"
        class_content = ''
        for i in range(0, (len(sanitize_table_lines))):
            class_content += f"    {sanitize_table_lines[i]}\n"
        complete_name = os.path.join(save_path, table_name.replace('agde_', '') + ".py")
        file = open(complete_name, "w")
        file.write(
            import_content +
            f"class {table_name.replace('agde_', '').title().replace('_', '')}(models.BaseFdb):\n"
            f"    __tablename__ = '{table_name}'\n\n"
            f"{class_content}"
        )
        if constraint_line:
            file.write(f"\n{constraint_line}\n")
        file.close()
