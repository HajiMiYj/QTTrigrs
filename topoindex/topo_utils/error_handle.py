from ..topo_utils.append_log_message import append_log_messageV1


def handle_tpindx_error(main_app, error_code,  init):
    """
    21    continue
    write (*,*) '*** Error opening intialization file ***'
    write (*,*) '--> ',trim(init)
    write (*,*) 'Check file name and location'
                write(*,*) 'Press RETURN to exit'
                read*
    stop
    # =======注意，这个几乎在python里是遇不到的，咱们不处理==========
    # 25    continue
    #  write (*,*) 'Error opening output file'
    # write (*,*) '--> ',trim(outfil)
    # write (*,*) 'Check file path and status'
    #             write(*,*) 'Press RETURN to exit'
    #             read*
    stop
    # =======注意，这个几乎在python里是遇不到的，咱们不处理==========
    30    continue
    write (*,*) '*** Error reading file ***'
    write (*,*) '--> ',trim(init)
    write (*,*) 'Check file format and data'
                write(*,*) 'Press RETURN to exit'
                read*
    stop
    35    continue
    write (*,*) '*** Premature end of file ***'
    write (*,*) '--> ',trim(init)
    write (*,*) 'Check file format and content'
                write(*,*) 'Press RETURN to exit'
                read*
    """
    if error_code == 21:
        append_log_messageV1(main_app, "*** Error opening initialization file ***")
        append_log_messageV1(main_app, f"--> {init}")
        append_log_messageV1(main_app, "Check file name and location.")
        pass
    # elif error_code == 25:
    #     pass
    elif error_code == 30:
        append_log_messageV1(main_app, '*** Error reading file ***')
        append_log_messageV1(main_app, f"--> {init}")
        append_log_messageV1(main_app, 'Check file format and data')
        pass
    elif error_code == 35:
        append_log_messageV1(main_app, '*** Premature end of file ***')
        append_log_messageV1(main_app, f"--> {init}")
        append_log_messageV1(main_app, 'Check file format and content')
        pass
