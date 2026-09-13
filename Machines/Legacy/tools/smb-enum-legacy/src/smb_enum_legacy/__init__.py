import argparse
import sys

from smb_enum_legacy import negotiate, session_setup, share_enum, transport, tree_connect


def enumerate_host(host: str, port: int = transport.DEFAULT_PORT, account_name: str = "") -> dict:
    sock = transport.connect(host, port)
    try:
        transport.send_smb(sock, negotiate.build_negotiate_request(mid=1))
        neg = negotiate.parse_negotiate_response(transport.recv_smb(sock))
        if not neg["smb1_supported"]:
            return {"host": host, "smb1_supported": False}

        transport.send_smb(
            sock,
            session_setup.build_session_setup_request(mid=2, account_name=account_name),
        )
        sess = session_setup.parse_session_setup_response(transport.recv_smb(sock))
        if not sess["success"]:
            return {"host": host, "smb1_supported": True, "negotiate": neg, "session_setup": sess}

        unc_path = f"\\\\{host}\\IPC$"
        transport.send_smb(
            sock,
            tree_connect.build_tree_connect_request(unc_path, uid=sess["uid"], mid=3),
        )
        tree = tree_connect.parse_tree_connect_response(transport.recv_smb(sock))
        if not tree["success"]:
            return {
                "host": host,
                "smb1_supported": True,
                "negotiate": neg,
                "session_setup": sess,
                "tree_connect": tree,
            }

        transport.send_smb(
            sock,
            share_enum.build_net_share_enum_request(uid=sess["uid"], tid=tree["tid"], mid=4),
        )
        shares = share_enum.parse_net_share_enum_response(transport.recv_smb(sock))

        return {
            "host": host,
            "smb1_supported": True,
            "negotiate": neg,
            "session_setup": sess,
            "tree_connect": tree,
            "share_enum": shares,
        }
    finally:
        sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Legacy SMBv1 enumeration (learning project)")
    parser.add_argument("host")
    parser.add_argument("-p", "--port", type=int, default=transport.DEFAULT_PORT)
    parser.add_argument(
        "-u", "--user", default="",
        help='account name for session setup (default: "" for a true null session; try "Guest" as a credential-free fallback)',
    )
    args = parser.parse_args()

    try:
        result = enumerate_host(args.host, args.port, account_name=args.user)
    except NotImplementedError:
        print("some module still has TODOs to fill in", file=sys.stderr)
        raise

    if not result["smb1_supported"]:
        print(f"{args.host}: does not support SMB1")
        return

    neg = result["negotiate"]
    print(f"{args.host}: SMB1 supported, dialect_index={neg['dialect_index']} security_mode={neg['security_mode']:#x}")

    sess = result.get("session_setup")
    if sess is None or not sess["success"]:
        print("  session setup failed:", sess)
        return
    print(f"  session: uid={sess['uid']} guest={sess['guest']} native_os={sess['native_os']!r}")

    tree = result.get("tree_connect")
    if tree is None or not tree["success"]:
        print("  tree connect to IPC$ failed:", tree)
        return
    print(f"  connected to IPC$: tid={tree['tid']}")

    shares = result.get("share_enum")
    if shares is None or not shares["success"]:
        print("  share enumeration failed:", shares)
        return
    print(f"  shares ({shares['entry_count']} of {shares['available_count']}):")
    for share in shares["shares"]:
        hidden = " [hidden]" if share["hidden"] else ""
        remark = f" -- {share['remark']}" if share["remark"] else ""
        print(f"    {share['name']}{hidden}{remark}")
