#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif

#include <windows.h>
#include <shellapi.h>
#include <stdlib.h>
#include <wchar.h>


typedef struct {
    wchar_t *data;
    size_t length;
    size_t capacity;
} TextBuffer;


static int reserve(TextBuffer *buffer, size_t extra) {
    size_t required = buffer->length + extra + 1;
    if (required <= buffer->capacity) {
        return 1;
    }
    size_t capacity = buffer->capacity ? buffer->capacity : 256;
    while (capacity < required) {
        capacity *= 2;
    }
    wchar_t *data = (wchar_t *)realloc(buffer->data, capacity * sizeof(wchar_t));
    if (data == NULL) {
        return 0;
    }
    buffer->data = data;
    buffer->capacity = capacity;
    return 1;
}


static int append_char(TextBuffer *buffer, wchar_t character) {
    if (!reserve(buffer, 1)) {
        return 0;
    }
    buffer->data[buffer->length++] = character;
    buffer->data[buffer->length] = L'\0';
    return 1;
}


static int append_text(TextBuffer *buffer, const wchar_t *text) {
    size_t length = wcslen(text);
    if (!reserve(buffer, length)) {
        return 0;
    }
    memcpy(buffer->data + buffer->length, text, length * sizeof(wchar_t));
    buffer->length += length;
    buffer->data[buffer->length] = L'\0';
    return 1;
}


static int append_quoted_argument(TextBuffer *buffer, const wchar_t *argument) {
    size_t backslashes = 0;
    if (!append_char(buffer, L'"')) {
        return 0;
    }
    for (const wchar_t *cursor = argument; *cursor; ++cursor) {
        if (*cursor == L'\\') {
            ++backslashes;
            continue;
        }
        if (*cursor == L'"') {
            for (size_t index = 0; index < backslashes * 2 + 1; ++index) {
                if (!append_char(buffer, L'\\')) {
                    return 0;
                }
            }
            backslashes = 0;
            if (!append_char(buffer, L'"')) {
                return 0;
            }
            continue;
        }
        while (backslashes > 0) {
            if (!append_char(buffer, L'\\')) {
                return 0;
            }
            --backslashes;
        }
        if (!append_char(buffer, *cursor)) {
            return 0;
        }
    }
    while (backslashes > 0) {
        if (!append_text(buffer, L"\\\\")) {
            return 0;
        }
        --backslashes;
    }
    return append_char(buffer, L'"');
}


static wchar_t *module_path(void) {
    DWORD capacity = 512;
    while (capacity <= 32768) {
        wchar_t *path = (wchar_t *)malloc(capacity * sizeof(wchar_t));
        if (path == NULL) {
            return NULL;
        }
        DWORD length = GetModuleFileNameW(NULL, path, capacity);
        if (length > 0 && length < capacity - 1) {
            return path;
        }
        free(path);
        capacity *= 2;
    }
    return NULL;
}


static void show_launch_error(DWORD error_code) {
    wchar_t message[768];
    _snwprintf(
        message,
        768,
        L"未找到或无法启动系统默认 Python。\n\n"
        L"请先安装 Python，并确保 python.exe 已加入系统 PATH。\n\n"
        L"Windows 错误代码：%lu",
        (unsigned long)error_code
    );
    message[767] = L'\0';
    MessageBoxW(NULL, message, L"缺少系统 Python", MB_OK | MB_ICONERROR);
}


#ifdef LAUNCHER_CONSOLE
int wmain(void) {
#else
int WINAPI wWinMain(
    HINSTANCE instance,
    HINSTANCE previous_instance,
    PWSTR command_line,
    int show_command
) {
    (void)instance;
    (void)previous_instance;
    (void)command_line;
    (void)show_command;
#endif

    int argument_count = 0;
    wchar_t **arguments = CommandLineToArgvW(GetCommandLineW(), &argument_count);
    wchar_t *self_path = module_path();
    if (arguments == NULL || self_path == NULL) {
        if (arguments != NULL) {
            LocalFree(arguments);
        }
        free(self_path);
        show_launch_error(ERROR_NOT_ENOUGH_MEMORY);
        return 1;
    }

    TextBuffer command = {0};
    int command_ok = append_quoted_argument(&command, L"python.exe")
        && append_char(&command, L' ')
        && append_quoted_argument(&command, self_path);
    for (int index = 1; command_ok && index < argument_count; ++index) {
        command_ok = append_char(&command, L' ')
            && append_quoted_argument(&command, arguments[index]);
    }

    if (!command_ok) {
        LocalFree(arguments);
        free(self_path);
        free(command.data);
        show_launch_error(ERROR_NOT_ENOUGH_MEMORY);
        return 1;
    }

    STARTUPINFOW startup_info;
    PROCESS_INFORMATION process_info;
    ZeroMemory(&startup_info, sizeof(startup_info));
    ZeroMemory(&process_info, sizeof(process_info));
    startup_info.cb = sizeof(startup_info);

#ifdef LAUNCHER_CONSOLE
    DWORD creation_flags = 0;
#else
    DWORD creation_flags = CREATE_NO_WINDOW;
#endif
    BOOL started = CreateProcessW(
        NULL,
        command.data,
        NULL,
        NULL,
        TRUE,
        creation_flags,
        NULL,
        NULL,
        &startup_info,
        &process_info
    );
    DWORD launch_error = started ? ERROR_SUCCESS : GetLastError();

    LocalFree(arguments);
    free(self_path);
    free(command.data);

    if (!started) {
        show_launch_error(launch_error);
        return 1;
    }

    WaitForSingleObject(process_info.hProcess, INFINITE);
    DWORD exit_code = 1;
    GetExitCodeProcess(process_info.hProcess, &exit_code);
    CloseHandle(process_info.hThread);
    CloseHandle(process_info.hProcess);
    return (int)exit_code;
}
