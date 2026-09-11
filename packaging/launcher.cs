using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

internal static class Program
{
    private const uint LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool SetDllDirectory(string lpPathName);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr LoadLibraryEx(string lpFileName, IntPtr hFile, uint dwFlags);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBox(IntPtr hWnd, string text, string caption, uint type);

    private static int Main(string[] args)
    {
        string dir = AppDir();
        Directory.SetCurrentDirectory(dir);
        SetDllDirectory(dir);
        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        Environment.SetEnvironmentVariable("PATH", dir + ";" + path);
        Environment.SetEnvironmentVariable("WALLPAPER_STUDIO_PACKAGED", "1");
        Environment.SetEnvironmentVariable("WALLPAPER_STUDIO_ROOT", dir);

        string pythonDll = Path.Combine(dir, "python312.dll");
        if (!File.Exists(pythonDll))
        {
            Fail(
                "\u6ca1\u6709 python312.dll\u3002\n" +
                "\u8bf7\u5220\u6389\u6574\u4e2a WallpaperStudio \u6587\u4ef6\u5939\uff0c\u518d\u89e3\u538b GitHub \u4e0b\u8f7d\u7684 client-Windows\u3002\n" +
                "\u4e0d\u8981\u53ea\u8986\u76d6 exe\uff0c\u4e5f\u4e0d\u8981\u4ece\u538b\u7f29\u5305\u91cc\u76f4\u63a5\u6253\u5f00\u3002");
            return 1;
        }

        IntPtr handle = LoadLibraryEx(pythonDll, IntPtr.Zero, LOAD_WITH_ALTERED_SEARCH_PATH);
        if (handle == IntPtr.Zero)
        {
            int code = Marshal.GetLastWin32Error();
            Fail(
                "\u65e0\u6cd5\u52a0\u8f7d python312.dll\uff08\u9519\u8bef " + code + "\uff09\u3002\n" +
                "\u8bf7\u5b89\u88c5 Microsoft Visual C++ 2015-2022 x64\uff1a\n" +
                "https://aka.ms/vs/17/release/vc_redist.x64.exe");
            try
            {
                Process.Start("https://aka.ms/vs/17/release/vc_redist.x64.exe");
            }
            catch
            {
            }
            return 1;
        }

        string pythonw = Path.Combine(dir, "pythonw.exe");
        string script = Path.Combine(dir, "run.py");
        if (!File.Exists(pythonw) || !File.Exists(script))
        {
            Fail("\u7f3a\u5c11 pythonw.exe \u6216 run.py\uff0c\u89e3\u538b\u4e0d\u5b8c\u6574\u3002\u8bf7\u5220\u6389\u65e7\u6587\u4ef6\u5939\u540e\u91cd\u65b0\u89e3\u538b\u3002");
            return 1;
        }

        var psi = new ProcessStartInfo
        {
            FileName = pythonw,
            WorkingDirectory = dir,
            UseShellExecute = false
        };
        psi.EnvironmentVariables["WALLPAPER_STUDIO_PACKAGED"] = "1";
        psi.EnvironmentVariables["WALLPAPER_STUDIO_ROOT"] = dir;
        psi.EnvironmentVariables["PATH"] = dir + ";" + path;
        psi.Arguments = BuildArgs(args);
        try
        {
            File.WriteAllText(Path.Combine(dir, "launcher.log"), psi.FileName + " " + psi.Arguments);
        }
        catch
        {
        }

        Process child;
        try
        {
            child = Process.Start(psi);
        }
        catch (Exception ex)
        {
            Fail("\u65e0\u6cd5\u542f\u52a8 pythonw.exe\uff1a" + ex.Message);
            return 1;
        }
        if (child == null)
        {
            Fail("\u65e0\u6cd5\u542f\u52a8 pythonw.exe\u3002");
            return 1;
        }
        child.WaitForExit();
        return child.ExitCode;
    }

    private static string AppDir()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        if (!string.IsNullOrEmpty(dir))
        {
            return dir.TrimEnd('\\', '/');
        }
        string file = Process.GetCurrentProcess().MainModule.FileName;
        return Path.GetDirectoryName(file);
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }

    private static string BuildArgs(string[] args)
    {
        var sb = new StringBuilder("run.py");
        if (args == null)
        {
            return sb.ToString();
        }
        foreach (string arg in args)
        {
            sb.Append(' ');
            if (arg.IndexOfAny(new[] { ' ', '"' }) >= 0)
            {
                sb.Append(Quote(arg));
            }
            else
            {
                sb.Append(arg);
            }
        }
        return sb.ToString();
    }

    private static void Fail(string text)
    {
        MessageBox(IntPtr.Zero, text, "\u58c1\u7eb8\u5de5\u574a", 0x10);
    }
}
